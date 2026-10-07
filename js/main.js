/* =========================================================
   에너지인력양성센터 AI 안내 데스크 — 프론트 동작
   1 메뉴(햄버거·현재 섹션 표시) · 2 다크 모드 · 3 프로그램 카드 → 유형 미리 선택
   4 AI 문의 도우미(검증 → fetch('/api/ask') → 결과 카드 / 실패 3종) · 5 문의하기 링크
   ========================================================= */
(function () {
  "use strict";

  // 문의하기 구글 폼 (B3 문의 자동화와 연결). 비어 있으면 버튼이 안내만 띄운다.
  const GOOGLE_FORM_URL = "";
  const REQUEST_TIMEOUT_MS = 20000;   // 지연/타임아웃 기준 20초
  const MAX_LENGTH = 1000;

  const MSG = {
    empty: "문의 내용을 입력하세요.",
    tooLong: "문의 내용은 1,000자 이내로 입력하세요.",
    apiError: "안내를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.",
    timeout: "응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.",
    network: "서버에 연결할 수 없습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요."
  };

  const $ = (id) => document.getElementById(id);

  /* ---------- 1. 메뉴 ---------- */
  const navToggle = $("navToggle");
  const siteNav = $("siteNav");

  navToggle.addEventListener("click", () => {
    const open = siteNav.classList.toggle("open");
    navToggle.setAttribute("aria-expanded", String(open));
    navToggle.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
  });
  // 메뉴 항목을 누르면 모바일 메뉴를 닫는다
  siteNav.querySelectorAll("a").forEach((a) =>
    a.addEventListener("click", () => {
      siteNav.classList.remove("open");
      navToggle.setAttribute("aria-expanded", "false");
    })
  );

  // 스크롤 위치에 따라 현재 섹션 메뉴를 강조
  const sections = ["home", "about", "programs", "ask", "faq"].map((id) => $(id));
  const navLinks = Array.from(siteNav.querySelectorAll("a[href^='#']"));
  const markActive = () => {
    const y = window.scrollY + 120;
    let current = sections[0];
    for (const s of sections) if (s.offsetTop <= y) current = s;
    navLinks.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === "#" + current.id));
  };
  window.addEventListener("scroll", markActive, { passive: true });
  markActive();

  /* ---------- 2. 다크 모드 (보너스 UX) ---------- */
  const themeToggle = $("themeToggle");
  const applyTheme = (theme) => {
    if (theme) document.documentElement.setAttribute("data-theme", theme);
    else document.documentElement.removeAttribute("data-theme");
    const dark = theme === "dark" || (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
    themeToggle.textContent = dark ? "☀️" : "🌙";
  };
  let savedTheme = null;
  try { savedTheme = localStorage.getItem("theme"); } catch (_) { /* 저장소 사용 불가 환경 */ }
  applyTheme(savedTheme);
  themeToggle.addEventListener("click", () => {
    const nowDark = document.documentElement.getAttribute("data-theme") === "dark" ||
      (!document.documentElement.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
    const next = nowDark ? "light" : "dark";
    applyTheme(next);
    try { localStorage.setItem("theme", next); } catch (_) { /* 무시 */ }
  });

  /* ---------- 3. 프로그램 카드 → 유형 미리 선택 ---------- */
  const askType = $("askType");
  const askQuestion = $("askQuestion");
  document.querySelectorAll("[data-prefill]").forEach((a) =>
    a.addEventListener("click", () => {
      askType.value = a.dataset.prefill;
      setTimeout(() => askQuestion.focus(), 400);
    })
  );

  /* ---------- 4. AI 문의 도우미 ---------- */
  const askForm = $("askForm");
  const askSubmit = $("askSubmit");
  const askError = $("askError");
  const charCount = $("charCount");
  const counterEl = charCount.parentElement;
  const questionField = askQuestion.closest(".field");

  const resultEmpty = $("resultEmpty");
  const resultError = $("resultError");
  const resultBody = $("resultBody");

  askQuestion.addEventListener("input", () => {
    const n = askQuestion.value.length;
    charCount.textContent = n;
    counterEl.classList.toggle("over", n >= MAX_LENGTH);
    if (n > 0) clearFieldError();
  });

  function showFieldError(msg) {
    askError.textContent = msg;
    askError.hidden = false;
    questionField.classList.add("invalid");
    askQuestion.focus();
  }
  function clearFieldError() {
    askError.hidden = true;
    questionField.classList.remove("invalid");
  }
  function setLoading(on) {
    askSubmit.disabled = on;
    askSubmit.querySelector(".btn-label").hidden = on;
    askSubmit.querySelector(".btn-loading").hidden = !on;
  }
  function showResultError(msg) {
    resultEmpty.hidden = true;
    resultBody.hidden = true;
    resultError.textContent = msg;
    resultError.hidden = false;
  }
  function fillList(el, items, emptyText) {
    el.innerHTML = "";
    const list = Array.isArray(items) ? items.filter((x) => typeof x === "string" && x.trim()) : [];
    if (list.length === 0) {
      const li = document.createElement("li");
      li.textContent = emptyText;
      el.appendChild(li);
      return;
    }
    for (const text of list) {
      const li = document.createElement("li");
      li.textContent = text;   // textContent 사용: 모델 출력이 HTML로 해석되지 않게
      el.appendChild(li);
    }
  }
  function renderResult(data) {
    $("rDepartment").textContent = data.department || "센터 총괄";
    fillList($("rSteps"), data.steps, "절차 정보가 없습니다. 담당자에게 문의하세요.");
    fillList($("rDocuments"), data.documents, "별도 서류 없음");
    $("rDuration").textContent = data.duration || "담당자 확인 필요";
    $("rNotes").textContent = data.notes || "정확한 내용은 담당자 확인이 필요합니다.";
    resultEmpty.hidden = true;
    resultError.hidden = true;
    resultBody.hidden = false;
    if (window.matchMedia("(max-width: 900px)").matches) {
      $("askResult").scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  let inFlight = false;
  askForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (inFlight) return;   // 중복 클릭 방지

    const type = askType.value;
    const question = askQuestion.value.trim();

    // 실패 처리 ① 빈 입력 — 요청을 보내지 않는다
    if (!question) return showFieldError(MSG.empty);
    if (question.length > MAX_LENGTH) return showFieldError(MSG.tooLong);
    clearFieldError();

    inFlight = true;
    setLoading(true);
    resultError.hidden = true;

    // 실패 처리 ③ 타임아웃 — 20초 후 요청 중단
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, question }),
        signal: controller.signal
      });

      let data = null;
      try { data = await res.json(); } catch (_) { data = null; }

      // 실패 처리 ② API 오류 4xx/5xx
      if (!res.ok) {
        const serverMsg = data && typeof data.error === "string" ? data.error : "";
        // 400(입력 문제)은 서버 메시지를 그대로, 그 외는 공통 안내
        showResultError(res.status === 400 && serverMsg ? serverMsg : MSG.apiError);
        return;
      }
      if (!data || typeof data !== "object") {
        showResultError(MSG.apiError);
        return;
      }
      renderResult(data);
    } catch (err) {
      if (err && err.name === "AbortError") showResultError(MSG.timeout);
      else showResultError(MSG.network);
    } finally {
      clearTimeout(timer);
      setLoading(false);
      inFlight = false;
    }
  });

  /* ---------- 5. 문의하기(구글 폼) ---------- */
  const contactLink = $("contactLink");
  if (GOOGLE_FORM_URL) {
    contactLink.href = GOOGLE_FORM_URL;
  } else {
    contactLink.addEventListener("click", (e) => {
      e.preventDefault();
      contactLink.textContent = "문의 폼 준비 중입니다";
      setTimeout(() => (contactLink.textContent = "문의하기 (구글 폼)"), 2000);
    });
  }
})();
