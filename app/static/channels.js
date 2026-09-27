/* Desktop email channel: a remembered choice of how to compose.
   On mobile, the mailto: link is left alone. */
(function () {
  if (!document.documentElement.classList.contains("desktop")) return;
  var KEY = "greensheet.mail";
  var WAYS = [
    ["app", "Mail app"],
    ["gmail", "Gmail"],
    ["outlook", "Outlook.com"],
    ["m365", "Microsoft 365"],
    ["copy", "Copy address and message"]
  ];
  function get() { try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; } }
  function set(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }
  function label(v) { for (var i = 0; i < WAYS.length; i++) if (WAYS[i][0] === v) return WAYS[i][1]; return ""; }
  function q(s) { return encodeURIComponent(s); }

  function go(way, a) {
    var to = a.dataset.to, su = a.dataset.subject, body = a.dataset.body;
    if (way === "gmail") {
      window.open("https://mail.google.com/mail/?view=cm&fs=1&to=" + q(to) + "&su=" + q(su) + "&body=" + q(body), "_blank", "noopener");
    } else if (way === "outlook") {
      window.open("https://outlook.live.com/mail/0/deeplink/compose?to=" + q(to) + "&subject=" + q(su) + "&body=" + q(body), "_blank", "noopener");
    } else if (way === "m365") {
      window.open("https://outlook.office.com/mail/deeplink/compose?to=" + q(to) + "&subject=" + q(su) + "&body=" + q(body), "_blank", "noopener");
    } else if (way === "copy") {
      var text = "To: " + to + "\nSubject: " + su + "\n\n" + body;
      var done = function () { flash(a, "Copied"); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, done);
      else { window.prompt("Copy this:", text); }
    } else {
      location.href = a.getAttribute("href");
    }
  }

  function flash(a, text) {
    var s = a.parentNode.querySelector(".ch-via");
    if (!s) return;
    var old = s.textContent; s.textContent = text;
    setTimeout(function () { s.textContent = old; }, 1400);
  }

  function closeMenus() {
    var open = document.querySelectorAll(".ch-menu");
    for (var i = 0; i < open.length; i++) open[i].parentNode.removeChild(open[i]);
  }

  function menu(a) {
    closeMenus();
    var m = document.createElement("span");
    m.className = "ch-menu";
    m.setAttribute("role", "menu");
    var t = document.createElement("span"); t.className = "ch-menu-title"; t.textContent = "Send email with"; m.appendChild(t);
    WAYS.forEach(function (w) {
      var b = document.createElement("button");
      b.type = "button"; b.setAttribute("role", "menuitem"); b.textContent = w[1];
      b.addEventListener("click", function (e) {
        e.preventDefault(); e.stopPropagation();
        set(w[0]); closeMenus(); decorate(); go(w[0], a);
      });
      m.appendChild(b);
    });
    a.parentNode.insertBefore(m, a.nextSibling);
    m.querySelector("button").focus();
  }

  function decorate() {
    var way = get();
    var links = document.querySelectorAll(".ch-email");
    for (var i = 0; i < links.length; i++) {
      var a = links[i], via = a.parentNode.querySelector(".ch-via");
      if (!via) { via = document.createElement("button"); via.type = "button"; via.className = "ch-via"; a.parentNode.insertBefore(via, a.nextSibling); }
      via.textContent = way ? "via " + label(way) : "";
      via.title = "Change how email is sent";
      via.hidden = !way;
    }
  }

  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest(".ch-email");
    var via = e.target.closest && e.target.closest(".ch-via");
    if (via) { e.preventDefault(); menu(via.previousSibling); return; }
    if (a) {
      var way = get();
      e.preventDefault();
      if (!way) menu(a); else go(way, a);
      return;
    }
    if (!e.target.closest || !e.target.closest(".ch-menu")) closeMenus();
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeMenus(); });
  document.addEventListener("htmx:afterSwap", decorate);
  decorate();
})();
