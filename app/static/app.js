"use strict";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const view = $("#view");

const MONTHS = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
const DOW = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"];
const DOW3 = ["lun","mar","mié","jue","vie","sáb","dom"];
const SECTIONS = ["Frutería","Carnicería","Pescadería","Huevos y lácteos","Panadería","Despensa","Congelados","Otros"];
const SECTION_EMOJI = { "Frutería": "🥕", "Carnicería": "🥩", "Pescadería": "🐟", "Huevos y lácteos": "🥚", "Panadería": "🥖", "Despensa": "🫙", "Congelados": "🧊", "Otros": "🛒" };
const GROUPS = {
  pescado:  { label: "Pescado",  emoji: "🐟" },
  carne:    { label: "Carne",    emoji: "🍗" },
  huevo:    { label: "Huevo",    emoji: "🍳" },
  legumbre: { label: "Legumbre", emoji: "🫘" },
  pasta:    { label: "Pasta",    emoji: "🍝" },
  arroz:    { label: "Arroz",    emoji: "🥘" },
  verdura:  { label: "Verdura",  emoji: "🥦" },
  patata:   { label: "Patata",   emoji: "🥔" },
  lacteo:   { label: "Lácteo",   emoji: "🧀" },
  fruta:    { label: "Fruta",    emoji: "🍎" },
};
const PRIORITY = ["pescado", "carne", "huevo", "legumbre", "pasta", "arroz", "patata", "verdura", "lacteo", "fruta"];
const KEYWORDS = {
  pescado: /pescad|merluza|bacalao|salm[oó]n|at[uú]n|pescadilla|gallo|lenguado|rape|dorada|lubina|sardina|boquer|caballa|abadejo|calamar|sepia|gamba|langostino|marisco|mejill|almeja|palometa|panga|bonito|fletan|emperador/i,
  carne: /carne|pollo|pavo|ternera|cerdo|lomo|alb[oó]ndiga|hamburguesa|filete|cordero|conejo|chorizo|jam[oó]n|salchicha|muslo|pechuga|cocido|magro|san jacobo|escalope|costilla|morcilla/i,
  huevo: /huevo|tortilla|revuelto|quiche/i,
  legumbre: /lenteja|garbanzo|alubia|jud[ií]on|frijol|habas|hummus|legumbre|fabada|potaje/i,
  pasta: /pasta|macarr|espagueti|fideo|tallar|lasa[ñn]a|canel[oó]n|tortellini|ravioli|fideu|estrellitas|plumas|h[eé]lices|lazos/i,
  arroz: /arroz|paella|risotto/i,
  patata: /patata|ensaladilla/i,
  verdura: /verdura|ensalada|crema|pur[eé]|menestra|jud[ií]as verdes|br[oó]coli|coliflor|calabac|calabaza|zanahoria|espinaca|acelga|pisto|tomate|lechuga|pimiento|berenjena|puerro|champi|guisante|alcachofa|sopa|gazpacho|salmorejo|repollo|boniato/i,
  lacteo: /yogur|queso|leche|natillas|flan|cuajada|l[aá]cteo|kefir/i,
  fruta: /fruta|manzana|pera|pl[aá]tano|naranja|mandarina|mel[oó]n|sand[ií]a|kiwi|uva|pi[ñn]a/i,
};

const state = { view: "home", date: iso(new Date()), week: null, month: null };

/* ---------- utilidades ---------- */
function iso(d) { const z = new Date(d.getTime() - d.getTimezoneOffset() * 60000); return z.toISOString().slice(0, 10); }
function parse(s) { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); }
function addDays(s, n) { const d = parse(s); d.setDate(d.getDate() + n); return iso(d); }
function wd(s) { return (parse(s).getDay() + 6) % 7; }
function mondayOf(s) { return addDays(s, -wd(s)); }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function fmt(s) { const d = parse(s); return `${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)}`; }
function cap(t) { return t.charAt(0).toUpperCase() + t.slice(1); }
function today() { return iso(new Date()); }

function groupsOf(textOrDish) {
  if (textOrDish && typeof textOrDish === "object" && textOrDish.groups?.length) return textOrDish.groups;
  const t = typeof textOrDish === "string" ? textOrDish : textOrDish?.name || "";
  return Object.keys(KEYWORDS).filter(g => KEYWORDS[g].test(t));
}
function mainGroup(x) { const gs = groupsOf(x); return PRIORITY.find(g => gs.includes(g)) || "otro"; }
function tile(x, cls = "") {
  const g = mainGroup(x);
  return `<div class="tile ${cls} g-${g}"><span class="emo">${GROUPS[g]?.emoji || "🍽️"}</span></div>`;
}
function groupMeta(d) {
  const gs = groupsOf(d).filter(g => GROUPS[g]).slice(0, 3).map(g => GROUPS[g].label);
  return gs.join(" · ");
}

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 2600);
}

async function api(path, opts = {}) {
  // redirect "manual": si Cloudflare Access (u otro proxy) pide volver a entrar, recargamos la página para que lo haga
  const o = { headers: {}, credentials: "same-origin", redirect: "manual", ...opts };
  if (o.body && !(o.body instanceof FormData)) { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(o.body); }
  const r = await fetch(path, o);
  if (r.type === "opaqueredirect" || r.status === 0) { location.reload(); throw new Error("Volviendo a iniciar sesión…"); }
  if (r.status === 401) { location.href = "/login"; throw new Error("Sesión caducada"); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `Error ${r.status}`);
  return data;
}
async function busy(btn, fn) {
  if (btn) btn.disabled = true;
  try { return await fn(); } catch (e) { toast(e.message); } finally { if (btn) btn.disabled = false; }
}
function skeleton() {
  view.innerHTML = `<div class="skeleton"><i style="height:34px;width:60%"></i><i style="height:58px"></i><i style="height:60px"></i><i style="height:180px"></i><i style="height:120px"></i></div>`;
}

/* ---------- hoja inferior ---------- */
function sheet(title, bodyHtml, { ok = "Guardar", cancel = "Cancelar" } = {}) {
  const dlg = $("#sheet");
  $("#sheet-title").textContent = title;
  $("#sheet-body").innerHTML = bodyHtml;
  $("#sheet-ok").textContent = ok;
  $("#sheet-ok").hidden = !ok;
  $(".sheet-actions .ghost", dlg).textContent = cancel;
  dlg.showModal();
  dlg.onclick = e => { if (e.target === dlg) dlg.close("cancel"); };
  return new Promise(res => dlg.addEventListener("close", () => res(dlg.returnValue === "ok" ? $("#sheet-body") : null), { once: true }));
}

/* =========================================================
   INICIO
   ========================================================= */
async function renderHome() {
  const mon = mondayOf(state.date);
  if (!state.week || state.week.monday !== mon) skeleton();
  const data = state.week = await api(`/api/week?date=${state.date}`);
  const day = data.days.find(d => d.date === state.date) || data.days[0];
  const isToday = day.date === today();
  const hour = new Date().getHours();
  const greet = hour < 14 ? "Buenos días" : hour < 21 ? "Buenas tardes" : "Buenas noches";
  const title = isToday ? (day.weekday < 5 ? "¿Qué cenamos hoy?" : "¿Qué comemos hoy?") : `${DOW[day.weekday]} ${parse(day.date).getDate()}`;
  const hasMenu = data.days.some(d => d.school && d.school.dishes.length);

  const cats = Object.entries(data.targets).map(([g, t]) => {
    const n = data.counts[g] || 0, p = Math.min(100, Math.round(n / t * 100));
    return `<div class="cat ${n < t ? "low" : ""}" title="${GROUPS[g].label}: ${n} de ${t} raciones recomendadas">
      <div class="circle" style="--p:${p}">${GROUPS[g].emoji}</div><span class="name">${GROUPS[g].label}</span><span class="num">${n}/${t}</span></div>`;
  }).join("");

  const strip = data.days.map(d => `<button class="dchip ${d.date === day.date ? "sel" : ""} ${d.date === today() ? "today" : ""} ${d.weekday >= 5 ? "weekend" : ""}" data-day="${d.date}">
      <span class="dw">${DOW3[d.weekday]}</span><span class="dn">${parse(d.date).getDate()}</span></button>`).join("");

  view.innerHTML = `
    <header class="hero-head">
      <div class="eyebrow">${isToday ? `${greet} · ` : ""}${cap(DOW[day.weekday])}, ${fmt(day.date)}</div>
      <h1>${esc(cap(title))}</h1>
    </header>
    <div class="pill-nav">
      <button class="icon-btn" id="prev" aria-label="Semana anterior">‹</button>
      <button class="pill grow" id="this-week">
        <svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2.5"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>
        Semana del ${fmt(mon)} al ${fmt(addDays(mon, 6))}</button>
      <button class="icon-btn" id="next" aria-label="Semana siguiente">›</button>
    </div>
    <div id="install-slot"></div>
    ${hasMenu ? "" : `<div class="banner orange"><div class="ico">📄</div><div class="txt"><b>Aún no hay menú del cole</b>
      El cole lo publica entre el día 1 y el 4 de cada mes y la app lo busca sola. También puedes buscarlo ahora.
      <div class="row"><button class="btn sm primary" data-go="settings">Buscar menú</button></div></div></div>`}
    <div class="cats" aria-label="Equilibrio de la semana">${cats}</div>
    <nav class="strip" aria-label="Días de la semana">${strip}</nav>
    ${day.weekday < 5 ? weekdayContent(day) : weekendContent(day, data)}
  `;

  $("#prev").onclick = () => { state.date = addDays(mon, -7); renderHome(); };
  $("#next").onclick = () => { state.date = addDays(mon, 7); renderHome(); };
  $("#this-week").onclick = () => { state.date = today(); renderHome(); };
  $$("[data-day]").forEach(b => b.onclick = () => { state.date = b.dataset.day; renderHome(); });
  $$("[data-go]").forEach(b => b.onclick = () => go(b.dataset.go));
  $(".dchip.sel")?.scrollIntoView({ inline: "center", block: "nearest" });
  bindMealActions();
  $("#regen-weekend")?.addEventListener("click", e => busy(e.currentTarget, async () => {
    await api(`/api/week/${mon}/weekend`, { method: "POST" }); await renderHome(); toast("Nuevo menú de fin de semana");
  }));
  Install.renderBanner($("#install-slot"));
  refreshShopCount();
}

function weekdayContent(day) {
  const s = day.school;
  let school;
  if (s && s.dishes.length) {
    const items = s.dishes.map((x, i) => `<li class="${i === s.dishes.length - 1 && s.dishes.length > 2 ? "dessert" : ""}">${esc(x)}</li>`).join("");
    school = `<div class="school">${tile(s.dishes.slice(0, 2).join(" "), "sm")}<div class="body"><ul>${items}</ul>
      ${s.note ? `<span class="note">${esc(s.note)}</span>` : ""}</div></div>`;
  } else {
    school = `<div class="school"><div class="tile sm g-otro"><span class="emo">${s?.note ? "🎉" : "🏫"}</span></div><div class="body">
      ${s?.note ? `<ul><li>${esc(s.note)}</li></ul><span class="empty">No hay cole: comida en casa</span>` : `<span class="empty">Sin menú del cole para este día</span>`}</div></div>`;
  }
  const hint = s && s.dinner_hint ? `<div class="tip"><span class="ico">💡</span><div>El cole recomienda para cenar: <b>${esc(s.dinner_hint)}</b></div></div>` : "";
  return `
    <section class="section">
      <div class="sec-head"><h2>En el cole</h2><button class="link muted" data-act="edit-school" data-date="${day.date}">Corregir</button></div>
      ${school}${hint}
    </section>
    ${day.comida ? mealSection(day, "comida", "Comida en casa") : ""}
    ${day.cena ? mealSection(day, "cena", "Para cenar") : ""}`;
}

function weekendContent(day, data) {
  const missing = data.deficits.map(g => GROUPS[g].label.toLowerCase());
  return `
    <div class="tip" style="margin-top:0"><span class="ico">🧭</span><div>${missing.length
      ? `Menú pensado para completar lo que ha faltado esta semana: <b>${missing.join(", ")}</b>.`
      : "La semana va equilibrada: el finde mantiene la variedad."}</div></div>
    ${mealSection(day, "comida", "Comida")}
    ${mealSection(day, "cena", "Cena")}
    <div class="actions" style="padding-top:18px"><button class="btn" id="regen-weekend">🔄 Proponer otro menú de finde</button></div>`;
}

function badgeFor(d) {
  if (!d) return "";
  if (d.source === "cole") return `<span class="badge green">Recomendado por el cole</span>`;
  if (d.source === "ia") return `<span class="badge">✨ Idea IA</span>`;
  if (d.source === "manual") return `<span class="badge">Tu plato</span>`;
  return "";
}

function mealSection(day, meal, title) {
  const p = day[meal];
  if (!p) return "";
  const ch = p.choice;
  const others = (p.options || []).map((o, i) => ({ o, i })).filter(({ o }) => !ch || o.name !== ch.name);
  const feature = ch
    ? `<div class="feature"><div style="position:relative">${tile(ch, "big")}${badgeFor(ch)}<span class="badge right">✓ Elegido</span></div>
        <div class="title">${esc(ch.name)}</div>
        <div class="meta">${esc(groupMeta(ch))}${ch.ingredients?.length ? `<span class="dot"></span>${ch.ingredients.length} ingredientes` : ""}</div></div>`
    : `<div class="feature out"><div style="position:relative"><div class="tile big g-otro"><span class="emo">🍽️</span></div></div>
        <div class="title">${meal === "cena" ? "Cenamos fuera" : "Comemos fuera"}</div><div class="meta">No entra en la lista de la compra</div></div>`;
  const carousel = others.length ? `
    <div class="sec-head" style="margin-top:18px"><h2 style="font-size:1.05rem">${ch ? "Otras ideas" : "Ideas"}</h2></div>
    <div class="carousel">${others.map(({ o, i }) => `
      <button class="ocard" data-act="choose" data-date="${day.date}" data-meal="${meal}" data-i="${i}">
        <div style="position:relative">${tile(o, "card-tile")}${o.source === "cole" ? `<span class="badge green">Cole</span>` : o.source === "ia" ? `<span class="badge">✨ IA</span>` : ""}<span class="plus">+</span></div>
        <div class="name">${esc(o.name)}</div><div class="meta">${esc(groupMeta(o))}</div>
      </button>`).join("")}</div>` : "";
  return `
    <section class="section">
      <div class="sec-head"><h2>${title}</h2></div>
      ${feature}
      <div class="actions">
        <button class="btn sm" data-act="regen" data-date="${day.date}" data-meal="${meal}">🔄 Más ideas</button>
        <button class="btn sm" data-act="custom" data-date="${day.date}" data-meal="${meal}">✏️ Otro plato</button>
        ${ch ? `<button class="btn sm" data-act="ings" data-date="${day.date}" data-meal="${meal}">🧾 Ingredientes</button>
                <button class="btn sm" data-act="clear" data-date="${day.date}" data-meal="${meal}">🚶 ${meal === "cena" ? "Cenamos fuera" : "Comemos fuera"}</button>` : ""}
      </div>
      ${carousel}
    </section>`;
}

function bindMealActions() {
  $$("[data-act]").forEach(b => b.addEventListener("click", e => {
    const { act, date, meal, i } = b.dataset;
    const btn = e.currentTarget;
    if (act === "choose") return busy(btn, async () => {
      await api(`/api/plan/${date}/${meal}/choose`, { method: "POST", body: { index: Number(i) } });
      await renderHome(); toast("¡Hecho! Añadido a la compra"); window.scrollTo({ top: 0, behavior: "smooth" });
    });
    if (act === "regen") return busy(btn, async () => { await api(`/api/plan/${date}/${meal}/regenerate`, { method: "POST" }); await renderHome(); });
    if (act === "clear") return busy(btn, async () => { await api(`/api/plan/${date}/${meal}`, { method: "DELETE" }); await renderHome(); toast("Quitado de la lista de la compra"); });
    if (act === "custom") return customDish(date, meal);
    if (act === "ings") return showIngredients(date, meal);
    if (act === "edit-school") return editSchool(date);
  }));
}

function showIngredients(date, meal) {
  const d = state.week.days.find(x => x.date === date);
  const ch = d[meal].choice;
  const rows = (ch.ingredients || []).map(i => `<li class="row"><span>${SECTION_EMOJI[i.section] || "🛒"}</span><div class="txt"><div class="t">${esc(i.name)}</div></div><span class="qty">${esc(i.qty)}</span></li>`).join("");
  sheet(ch.name, rows ? `<ul class="list" style="padding:0">${rows}</ul>` : `<p class="help">Este plato no tiene ingredientes guardados. Usa “Otro plato” para añadirlos.</p>`, { ok: "", cancel: "Cerrar" });
}

async function customDish(date, meal) {
  const body = await sheet(`${meal === "cena" ? "Cena" : "Comida"} del ${DOW[wd(date)]} ${fmt(date)}`, `
    <label class="f" for="cd-name">Plato</label>
    <input type="text" id="cd-name" list="recipe-list" placeholder="Ej.: Crema de calabaza y tortilla" autocomplete="off" required>
    <label class="f" for="cd-ings">Ingredientes <span style="font-weight:500;color:var(--muted)">(opcional)</span></label>
    <textarea id="cd-ings" placeholder="Uno por línea, con la cantidad tras un guion:&#10;Calabaza - 1 kg&#10;Huevos - 6"></textarea>
    <p class="help">Si eliges un plato de la lista y dejas los ingredientes vacíos, se usan los del recetario.</p>`);
  if (!body) return;
  const name = $("#cd-name", body).value.trim();
  if (!name) return;
  const raw = $("#cd-ings", body).value.trim();
  const ingredients = raw ? raw.split("\n").map(l => l.trim()).filter(Boolean).map(l => {
    const [n, ...q] = l.split(/\s+[-–:]\s+/); return { name: n.trim(), qty: q.join(" ").trim(), section: guessSection(n) };
  }) : undefined;
  await busy(null, async () => { await api(`/api/plan/${date}/${meal}/choose`, { method: "POST", body: { name, ingredients } }); await renderHome(); toast("Guardado"); });
}

function guessSection(n) {
  const s = n.toLowerCase();
  if (/(merluza|salm[oó]n|bacalao|gamba|langostino|pescad|sardina|dorada|lubina|calamar|sepia|mejill|almeja|rape|gallo)/.test(s)) return "Pescadería";
  if (/(pollo|pavo|ternera|cerdo|carne|lomo|chorizo|jam[oó]n|salchicha|hamburguesa)/.test(s)) return "Carnicería";
  if (/(huevo|leche|yogur|queso|nata|mantequilla|quesito)/.test(s)) return "Huevos y lácteos";
  if (/(^pan|masa|tortillas de trigo)/.test(s)) return "Panadería";
  if (/(arroz|pasta|macarr|espagueti|fideo|lenteja|garbanzo|alubia|aceite|harina|sal\b|lata|tomate frito|tomate triturado|especia|piment[oó]n|comino|azafr)/.test(s)) return "Despensa";
  if (/congelad/.test(s)) return "Congelados";
  return "Frutería";
}

async function editSchool(date) {
  const d = state.week.days.find(x => x.date === date);
  const s = d.school || { dishes: [], dinner_hint: "", note: "" };
  const body = await sheet(`Menú del cole · ${DOW[d.weekday]} ${fmt(date)}`, `
    <label class="f" for="es-dishes">Platos (uno por línea)</label>
    <textarea id="es-dishes">${esc(s.dishes.join("\n"))}</textarea>
    <label class="f" for="es-hint">Recomendación de cena del cole</label>
    <input type="text" id="es-hint" value="${esc(s.dinner_hint)}" placeholder="Ej.: Pescado y verdura">
    <label class="f" for="es-note">Nota</label>
    <input type="text" id="es-note" value="${esc(s.note)}" placeholder="Ej.: Festivo">
    <p class="help">Tus correcciones se respetan aunque se vuelva a descargar el PDF.</p>`);
  if (!body) return;
  await busy(null, async () => {
    await api(`/api/school/${date}`, { method: "PUT", body: {
      dishes: $("#es-dishes", body).value.split("\n"), dinner_hint: $("#es-hint", body).value.trim(), note: $("#es-note", body).value.trim() } });
    await renderHome(); toast("Menú corregido");
  });
}

/* =========================================================
   MES
   ========================================================= */
async function renderMonth() {
  const d = parse(state.date);
  const y = state.month?.y ?? d.getFullYear(), m = state.month?.m ?? d.getMonth() + 1;
  state.month = { y, m };
  skeleton();
  const data = await api(`/api/month?year=${y}&month=${m}`);
  const days = data.days.filter(x => wd(x.date) < 5);
  const first = wd(days[0].date);
  const blanks = Array.from({ length: first }, () => `<div class="mcell blank" aria-hidden="true"></div>`).join("");
  const cells = days.map(x => {
    const emos = x.dishes.slice(0, 2).map(s => GROUPS[mainGroup(s)]?.emoji || "").join("");
    return `<button class="mcell ${x.date === today() ? "today" : ""}" data-date="${x.date}">
      <span class="n">${parse(x.date).getDate()}</span>
      ${x.note ? `<span class="hol">${esc(x.note)}</span>` : ""}
      ${emos ? `<span class="emos">${emos}</span>` : ""}
      ${x.dishes[0] ? `<span class="d">${esc(x.dishes.slice(0, 2).join(" · "))}</span>` : ""}
    </button>`;
  }).join("");
  view.innerHTML = `
    <header class="hero-head">
      <div class="eyebrow">${data.menu ? esc(data.menu.title || "Menú del cole") : "Sin menú del cole"}</div>
      <h1 style="text-transform:capitalize">${MONTHS[m - 1]} ${y}</h1>
    </header>
    <div class="pill-nav">
      <button class="icon-btn" id="mprev" aria-label="Mes anterior">‹</button>
      ${data.menu ? `<a class="pill grow" href="/api/menus/${y}/${m}/pdf" target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>Ver PDF del cole</a>` : `<span class="pill grow">Sin PDF</span>`}
      <button class="icon-btn" id="mnext" aria-label="Mes siguiente">›</button>
    </div>
    <div class="month">${["L","M","X","J","V"].map(x => `<div class="dow">${x}</div>`).join("")}${blanks}${cells}</div>
    <p class="help pad" style="margin-top:12px">Toca un día para ver qué comen y elegir la cena.</p>`;
  $("#mprev").onclick = () => { state.month = m === 1 ? { y: y - 1, m: 12 } : { y, m: m - 1 }; renderMonth(); };
  $("#mnext").onclick = () => { state.month = m === 12 ? { y: y + 1, m: 1 } : { y, m: m + 1 }; renderMonth(); };
  $$(".mcell[data-date]").forEach(b => b.onclick = () => { state.date = b.dataset.date; go("home"); });
}

/* =========================================================
   COMPRA
   ========================================================= */
async function renderShop() {
  skeleton();
  const data = await api(`/api/shopping?date=${state.date}`);
  const mon = data.week;
  const bySec = {};
  data.items.forEach(it => (bySec[it.section] ||= []).push(it));
  const total = data.items.length, done = data.items.filter(i => i.checked).length;
  setShopCount(total - done);
  view.innerHTML = `
    <header class="hero-head">
      <div class="eyebrow">Semana del ${fmt(mon)} al ${fmt(addDays(mon, 6))}</div>
      <h1>Lista de la compra</h1>
    </header>
    <div class="pill-nav">
      <button class="icon-btn" id="sprev" aria-label="Semana anterior">‹</button>
      <span class="pill grow">${total - done} por comprar · ${done} en el carro</span>
      <button class="icon-btn" id="snext" aria-label="Semana siguiente">›</button>
    </div>
    <div class="progress" aria-hidden="true"><i style="width:${total ? Math.round(done / total * 100) : 0}%"></i></div>
    <form class="add" id="add" style="margin-top:14px">
      <input type="text" id="add-name" placeholder="Añadir algo más…" aria-label="Producto" autocomplete="off">
      <select id="add-sec" aria-label="Sección">${SECTIONS.map(s => `<option ${s === "Otros" ? "selected" : ""}>${s}</option>`).join("")}</select>
      <button class="btn primary sm" aria-label="Añadir">Añadir</button>
    </form>
    ${total ? Object.entries(bySec).map(([sec, items]) => `
      <section class="shop-sec"><h3>${SECTION_EMOJI[sec] || "🛒"} ${esc(sec)}</h3><ul class="list">
        ${items.map(it => `<li class="row ${it.checked ? "done" : ""}">
          <input type="checkbox" class="check" ${it.checked ? "checked" : ""} data-name="${esc(it.name)}" aria-label="${esc(it.name)}">
          <div class="txt"><div class="t">${esc(it.name)}</div>${it.for.length ? `<div class="s">${esc(it.for.join(" · "))}</div>` : ""}</div>
          ${it.qty ? `<span class="qty">${esc(it.qty)}</span>` : ""}
          <button class="x" data-hide="${esc(it.name)}" aria-label="Quitar ${esc(it.name)}">×</button></li>`).join("")}
      </ul></section>`).join("") : `<div class="empty-state"><div class="big">🛒</div><b>La lista está vacía</b>Elige cenas y el menú del finde en Inicio y aparecerán aquí sus ingredientes.</div>`}
    ${total ? `<div class="sticky-cta"><button class="btn primary block" id="share">Compartir lista</button>${done ? `<button class="btn" id="clear">Quitar comprado</button>` : ""}</div>` : ""}`;
  const reload = () => renderShop();
  $("#sprev").onclick = () => { state.date = addDays(mon, -7); reload(); };
  $("#snext").onclick = () => { state.date = addDays(mon, 7); reload(); };
  $("#add").onsubmit = async e => {
    e.preventDefault(); const name = $("#add-name").value.trim(); if (!name) return;
    await busy(null, () => api("/api/shopping", { method: "POST", body: { date: mon, name, section: $("#add-sec").value } })); reload();
  };
  $$(".check").forEach(cb => cb.onchange = async () => {
    cb.closest(".row").classList.toggle("done", cb.checked);
    if (navigator.vibrate) navigator.vibrate(8);
    await busy(null, () => api("/api/shopping", { method: "PATCH", body: { date: mon, name: cb.dataset.name, checked: cb.checked } }));
    const left = $$(".check").filter(c => !c.checked).length;
    setShopCount(left);
    $(".pill.grow").textContent = `${left} por comprar · ${total - left} en el carro`;
    $(".progress i").style.width = `${Math.round((total - left) / total * 100)}%`;
  });
  $$("[data-hide]").forEach(b => b.onclick = async () => {
    await busy(b, () => api("/api/shopping", { method: "PATCH", body: { date: mon, name: b.dataset.hide, hidden: true } })); reload();
  });
  $("#clear")?.addEventListener("click", async e => { await busy(e.currentTarget, () => api("/api/shopping/clear-checked", { method: "POST", body: { date: mon } })); reload(); });
  $("#share")?.addEventListener("click", async () => {
    const text = `🛒 Compra semana del ${fmt(mon)}\n` + Object.entries(bySec).map(([sec, items]) => {
      const left = items.filter(i => !$$(".check").find(c => c.dataset.name === i.name)?.checked);
      return left.length ? `\n${sec}:\n` + left.map(i => `• ${i.name}${i.qty ? ` (${i.qty})` : ""}`).join("\n") : "";
    }).join("");
    if (navigator.share) { try { await navigator.share({ title: "Lista de la compra", text }); return; } catch (_) { return; } }
    try { await navigator.clipboard.writeText(text); toast("Lista copiada"); } catch (_) { toast("No se pudo copiar"); }
  });
}

function setShopCount(n) {
  const b = $("#shop-count");
  b.hidden = !n; b.textContent = n > 99 ? "99+" : n;
}
async function refreshShopCount() {
  try { const d = await api(`/api/shopping?date=${state.date}`); setShopCount(d.items.filter(i => !i.checked).length); } catch (_) { }
}

/* =========================================================
   AJUSTES
   ========================================================= */
async function renderSettings() {
  skeleton();
  const s = await api("/api/status");
  view.innerHTML = `
    <header class="hero-head"><div class="eyebrow">Configuración</div><h1>Ajustes</h1></header>

    <div class="sec-head"><h2>Instalar la app</h2></div>
    <div id="install-card"></div>

    <div class="sec-head"><h2>Menú del cole</h2></div>
    <div class="group">
      <div class="item"><span class="ico">🏫</span><div class="txt"><b>Web del comedor</b><span><a href="${esc(s.source)}" target="_blank" rel="noopener">${esc(s.source.replace(/^https?:\/\//, ""))}</a></span></div></div>
      <div class="item"><span class="ico">🕒</span><div class="txt"><b>Última revisión</b><span>${esc(s.last_check || "todavía no")}${s.last_check_result ? ` · ${esc(s.last_check_result)}` : ""}</span></div></div>
      <div class="item"><span class="ico">${s.ai ? "✨" : "📄"}</span><div class="txt"><b>Lectura del PDF</b><span>${s.ai ? `Con IA (${esc(s.ai)})` : "Lector automático sin IA. Añade una clave de OpenAI o Anthropic para más precisión."}</span></div></div>
      <div class="item" style="gap:8px;flex-wrap:wrap">
        <button class="btn primary" id="fetch">Buscar el menú ahora</button>
        <button class="btn" id="refetch" style="background:var(--bg)">Volver a importar</button>
      </div>
    </div>

    <div class="sec-head"><h2>Subir el PDF a mano</h2></div>
    <div class="group"><form id="up" class="item" style="flex-wrap:wrap">
      <input type="file" accept="application/pdf" id="pdf" required style="flex:1;min-width:0">
      <button class="btn primary sm">Importar</button></form></div>

    <div class="sec-head"><h2>Menús importados</h2></div>
    <div class="group">${s.menus.length ? s.menus.map(m => `
      <a class="item" href="/api/menus/${m.year}/${m.month}/pdf" target="_blank" rel="noopener" style="text-decoration:none">
        <span class="ico">📅</span><div class="txt"><b style="text-transform:capitalize">${MONTHS[m.month - 1]} ${m.year}</b><span>${esc(m.title || "")} · ${m.parser === "ia" ? "IA" : "lector"} · ${esc(m.fetched_at)}</span></div><span>›</span></a>`).join("")
      : `<div class="item"><span class="ico">📭</span><div class="txt">Ninguno todavía</div></div>`}</div>

    <div class="sec-head"><h2>Registro</h2></div>
    <div class="group"><ul class="logs">${s.logs.map(l => `<li class="${l.level}">${esc(l.at)} · ${esc(l.message)}</li>`).join("") || "<li>Sin actividad</li>"}</ul></div>
    ${s.auth ? `<div class="pad"><a class="btn block" href="/logout">Cerrar sesión</a></div>` : ""}`;

  Install.renderCard($("#install-card"));
  const fetchMenu = force => async e => busy(e.currentTarget, async () => {
    const r = await api(`/api/fetch${force ? "?force=1" : ""}`, { method: "POST" });
    toast(r.results.join(" · ")); state.week = null; renderSettings();
  });
  $("#fetch").onclick = fetchMenu(false);
  $("#refetch").onclick = fetchMenu(true);
  $("#up").onsubmit = async e => {
    e.preventDefault();
    const f = $("#pdf").files[0]; if (!f) return;
    const fd = new FormData(); fd.append("pdf", f);
    await busy(e.submitter, async () => {
      const r = await api("/api/upload", { method: "POST", body: fd });
      toast(`Importado ${MONTHS[r.month - 1]} ${r.year}: ${r.days} días`); state.week = null; renderSettings();
    });
  };
}

/* =========================================================
   INSTALACIÓN (web app)
   ========================================================= */
const SHARE_ICON = `<span class="kbd"><svg viewBox="0 0 24 24"><path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg></span>`;
const Install = {
  deferred: null,
  standalone: () => matchMedia("(display-mode: standalone)").matches || navigator.standalone === true,
  ios: () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1),
  android: () => /android/i.test(navigator.userAgent),
  dismissed() { try { return localStorage.getItem("install-dismissed") === "1"; } catch (_) { return false; } },
  dismiss() { try { localStorage.setItem("install-dismissed", "1"); } catch (_) { } },
  async prompt() {
    if (!this.deferred) return false;
    this.deferred.prompt();
    const { outcome } = await this.deferred.userChoice;
    this.deferred = null;
    if (outcome === "accepted") toast("¡App instalada!");
    return true;
  },
  howTo() {
    if (this.ios()) return `<ol class="steps"><li>Abre esta página en <b>Safari</b>.</li><li>Pulsa ${SHARE_ICON} <b>Compartir</b>.</li><li>Elige <b>Añadir a pantalla de inicio</b> y pulsa <b>Añadir</b>.</li></ol>`;
    if (this.android()) return `<ol class="steps"><li>Abre el menú <b>⋮</b> de Chrome.</li><li>Pulsa <b>Instalar aplicación</b> (o <b>Añadir a pantalla de inicio</b>).</li></ol>`;
    return `<ol class="steps"><li>En Chrome o Edge, pulsa el icono de <b>instalar</b> de la barra de direcciones.</li><li>En el móvil: Safari → Compartir → Añadir a pantalla de inicio (iPhone) o Chrome → ⋮ → Instalar aplicación (Android).</li></ol>`;
  },
  secureNote() {
    return window.isSecureContext ? "" :
      `<p class="help">⚠️ Estás entrando por <b>http</b>. En iPhone funciona igual, pero en Android solo se crea un acceso directo y no funciona sin conexión. Para la app completa, entra por <b>https</b> (mira el README).</p>`;
  },
  renderBanner(slot) {
    if (!slot || this.standalone() || this.dismissed()) return;
    if (!this.deferred && !this.ios() && !this.android()) return;
    slot.innerHTML = `<div class="banner green"><div class="ico">📲</div><div class="txt"><b>Instala Menú familiar</b>
      Tenla en la pantalla de inicio como una app más.
      <div class="row"><button class="btn sm primary" id="inst-go">${this.deferred ? "Instalar" : "Cómo instalar"}</button></div></div>
      <button class="close" id="inst-x" aria-label="Cerrar">✕</button></div>`;
    $("#inst-x", slot).onclick = () => { this.dismiss(); slot.innerHTML = ""; };
    $("#inst-go", slot).onclick = async () => { if (!(await this.prompt())) this.showHelp(); else slot.innerHTML = ""; };
  },
  renderCard(el) {
    if (this.standalone()) {
      el.innerHTML = `<div class="group"><div class="item"><span class="ico">✅</span><div class="txt"><b>Ya estás usando la app instalada</b><span>Se actualiza sola cuando hay versión nueva.</span></div></div></div>`;
      return;
    }
    el.innerHTML = `<div class="group"><div class="item" style="align-items:flex-start"><span class="ico">📲</span><div class="txt">
      <b>Añádela a tu móvil u ordenador</b><span>Funciona en iPhone, Android y escritorio, a pantalla completa y con su propio icono.</span>
      ${this.deferred ? "" : this.howTo()}${this.secureNote()}
      ${this.deferred ? `<div style="margin-top:10px"><button class="btn primary sm" id="inst-btn">Instalar ahora</button></div>` : ""}
      </div></div></div>`;
    $("#inst-btn", el)?.addEventListener("click", () => this.prompt());
  },
  showHelp() { sheet("Instalar en el móvil", this.howTo() + this.secureNote(), { ok: "", cancel: "Entendido" }); },
};
window.addEventListener("beforeinstallprompt", e => {
  e.preventDefault(); Install.deferred = e;
  if (state.view === "home") Install.renderBanner($("#install-slot"));
  if (state.view === "settings") Install.renderCard($("#install-card"));
});
window.addEventListener("appinstalled", () => { Install.deferred = null; $("#install-slot") && ($("#install-slot").innerHTML = ""); });

if ("serviceWorker" in navigator && window.isSecureContext) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
function onlineBanner() {
  let b = $(".offline");
  if (navigator.onLine) { b?.remove(); return; }
  if (!b) { b = document.createElement("div"); b.className = "offline"; b.textContent = "Sin conexión · mostrando lo último guardado"; document.body.append(b); }
}
window.addEventListener("online", onlineBanner);
window.addEventListener("offline", onlineBanner);

/* ---------- navegación ---------- */
const RENDER = { home: renderHome, month: renderMonth, shop: renderShop, settings: renderSettings };
function go(v) {
  if (v === "week") v = "home";
  state.view = v;
  $$(".tabbar button").forEach(b => b.classList.toggle("active", b.dataset.view === v));
  history.replaceState(null, "", `#${v}`);
  window.scrollTo({ top: 0 });
  RENDER[v]().catch(e => { view.innerHTML = `<div class="empty-state"><div class="big">😕</div><b>Algo ha fallado</b>${esc(e.message)}</div>`; });
}
$$(".tabbar button").forEach(b => b.onclick = () => { if (b.dataset.view === "home" && state.view === "home") state.date = today(); go(b.dataset.view); });

api("/api/recipes").then(r => { $("#recipe-list").innerHTML = r.recipes.map(x => `<option value="${esc(x.name)}">`).join(""); }).catch(() => {});
const initial = location.hash.slice(1);
onlineBanner();
go(RENDER[initial] || initial === "week" ? initial : "home");
