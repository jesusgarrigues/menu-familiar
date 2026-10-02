"use strict";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const view = $("#view");

const MONTHS = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
const DOW = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"];
const DOW3 = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"];
const SECTIONS = ["Frutería","Carnicería","Pescadería","Huevos y lácteos","Panadería","Despensa","Congelados","Otros"];
const ALLERGENS = { 1: "gluten", 2: "crustáceos", 3: "huevo", 4: "pescado", 5: "cacahuete", 6: "soja", 7: "leche",
  8: "frutos de cáscara", 9: "apio", 10: "mostaza", 11: "sésamo", 12: "sulfitos", 13: "altramuces", 14: "moluscos" };
const GROUP_LABEL = { pescado: "Pescado", carne: "Carne", huevo: "Huevo", legumbre: "Legumbre", pasta: "Pasta", arroz: "Arroz",
  verdura: "Verdura", patata: "Patata", lacteo: "Lácteo", fruta: "Fruta" };
const PRIORITY = ["pescado", "carne", "huevo", "legumbre", "pasta", "arroz", "patata", "verdura", "lacteo", "fruta"];
const KEYWORDS = {
  pescado: /pescad|merluza|bacalao|salm[oó]n|at[uú]n|pescadilla|gallo|lenguado|rape|dorada|lubina|sardina|boquer|caballa|abadejo|calamar|sepia|gamba|langostino|marisco|mejill|almeja|palometa|panga|bonito|fletan|emperador/i,
  carne: /carne|pollo|pavo|ternera|cerdo|lomo|alb[oó]ndiga|hamburguesa|filete|cordero|conejo|chorizo|jam[oó]n|salchicha|muslo|pechuga|cocido|magro|san jacobo|escalope|costilla|morcilla/i,
  huevo: /huevo|tortilla|revuelto|quiche/i,
  legumbre: /lenteja|garbanzo|alubia|jud[ií]as blancas|jud[ií]on|frijol|habas|hummus|legumbre|fabada|potaje/i,
  pasta: /pasta|macarr|espagueti|fideo|tallar|lasa[ñn]a|canel[oó]n|tortellini|ravioli|fideu|estrellitas|plumas|h[eé]lices|lazos/i,
  arroz: /arroz|paella|risotto/i,
  patata: /patata|ensaladilla/i,
  verdura: /verdura|ensalada|crema|pur[eé]|menestra|jud[ií]as verdes|br[oó]coli|coliflor|calabac|calabaza|zanahoria|espinaca|acelga|pisto|tomate|lechuga|pimiento|berenjena|puerro|champi|guisante|alcachofa|sopa|gazpacho|salmorejo|repollo|boniato/i,
  lacteo: /yogur|queso|leche|natillas|flan|cuajada|l[aá]cteo|kefir/i,
  fruta: /fruta|manzana|pera|pl[aá]tano|naranja|mandarina|mel[oó]n|sand[ií]a|kiwi|uva|pi[ñn]a/i,
};
const DESSERT = /fruta|yogur|natillas|flan|postre|helado|cuajada|macedonia|compota|manzana|pera|pl[aá]tano|naranja|mandarina|kiwi|l[aá]cteo|arroz con leche|bizcocho/i;

const ICON = {
  camera: '<svg viewBox="0 0 24 24"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="M5 12l5 5 9-10"/></svg>',
  bulb: '<svg viewBox="0 0 24 24"><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.8.8 1 1.5 1 2.5h6c0-1 .2-1.7 1-2.5A6 6 0 0 0 12 3z"/></svg>',
  cal: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2.5"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>',
  doc: '<svg viewBox="0 0 24 24"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>',
  close: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  refresh: '<svg viewBox="0 0 24 24"><path d="M20 11a8 8 0 0 0-14.7-4.3M4 4v4h4M4 13a8 8 0 0 0 14.7 4.3M20 20v-4h-4"/></svg>',
  pencil: '<svg viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/></svg>',
  list: '<svg viewBox="0 0 24 24"><path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01"/></svg>',
  out: '<svg viewBox="0 0 24 24"><path d="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10"/></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
};

const state = { view: "home", date: iso(new Date()), week: null, month: null, photos: false, after: null };

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

function groupsOf(x) {
  if (x && typeof x === "object" && x.groups?.length) return x.groups;
  const t = typeof x === "string" ? x : x?.name || "";
  return Object.keys(KEYWORDS).filter(g => KEYWORDS[g].test(t));
}
function mainGroup(x) { const gs = groupsOf(x); return PRIORITY.find(g => gs.includes(g)) || "otro"; }
function groupMeta(d) { return groupsOf(d).filter(g => GROUP_LABEL[g]).slice(0, 3).map(g => GROUP_LABEL[g]).join(" · "); }
function allergenText(list) { return (list || []).map(n => ALLERGENS[n] || n).join(", "); }

function courses(dishes) {
  return dishes.map((d, i) => {
    const last = i === dishes.length - 1 && dishes.length >= 3 && DESSERT.test(d);
    return { label: last ? "Postre" : `${i + 1}.º`, dish: d, dessert: last };
  });
}

/* Foto de un plato: marcador de color con icono; encima, la foto real cuando existe */
function photo(name, cls = "", { retry = false } = {}) {
  const g = mainGroup(name);
  const again = retry && state.photos && name
    ? `<button class="ph-retry" data-reject="${esc(name)}" aria-label="Buscar otra foto de ${esc(name)}" title="Buscar otra foto">${ICON.refresh}</button>` : "";
  const img = state.photos && name
    ? `<img alt="" loading="lazy" decoding="async" src="/api/photo?name=${encodeURIComponent(name)}" onload="this.parentNode.classList.add('loaded')" onerror="photoRetry(this)">`
    : "";
  return `<div class="ph g-${g} ${cls}" role="img" aria-label="${esc(name ? "Foto: " + name : "Sin foto")}"><span class="ph-ico">${ICON.camera}</span>${img}${again}</div>`;
}
document.addEventListener("click", async e => {
  const b = e.target.closest("[data-reject]");
  if (!b) return;
  e.stopPropagation();
  b.disabled = true;
  try {
    await api("/api/photo/reject", { method: "POST", body: { name: b.dataset.reject } });
    toast("Buscando otra foto…");
    const ph = b.closest(".ph");
    ph.classList.remove("loaded");
    const img = ph.querySelector("img");
    if (img) { img.dataset.tries = 0; setTimeout(() => { img.src = img.src.replace(/&t=\d+$/, "") + `&t=${Date.now()}`; }, 5000); }
  } catch (err) { toast(err.message); } finally { b.disabled = false; }
}, true);

window.photoRetry = img => {
  const n = Number(img.dataset.tries || 0);
  if (n >= 8) { img.remove(); return; }
  img.dataset.tries = n + 1;
  setTimeout(() => { if (img.isConnected) img.src = img.src.replace(/&t=\d+$/, "") + `&t=${Date.now()}`; }, 4000 + n * 4000);
};

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 2600);
}

async function api(path, opts = {}) {
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
  view.innerHTML = `<div class="skeleton"><i style="height:34px;width:60%"></i><i style="height:44px"></i><i style="height:60px"></i><i style="height:200px"></i><i style="height:140px"></i></div>`;
}
async function refresh() { await (state.after || renderHome)(); }

/* ---------- hoja de formulario ---------- */
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
   Piezas comunes: menú del cole y bloque de comida/cena
   ========================================================= */
function schoolCard(day, { compact = false } = {}) {
  const s = day.school;
  if (!s || !s.dishes.length) {
    return `<div class="school-card empty"><div class="sc-body"><span class="muted">${s?.note ? esc(s.note) + " · no hay cole" : "Sin menú del cole para este día"}</span></div></div>`;
  }
  const rows = courses(s.dishes).map((c, i) => `
    <div class="course ${c.dessert ? "dessert" : ""}">
      <span class="c-label">${c.label}</span>
      <div class="c-body"><span class="c-dish">${esc(c.dish)}</span>
      ${s.allergens?.[i]?.length ? `<span class="c-all">Alérgenos: ${esc(allergenText(s.allergens[i]))}</span>` : ""}</div>
    </div>`).join("");
  const list = courses(s.dishes);
  const slides = compact ? "" : `<div class="sc-carousel" data-carousel>
      <div class="sc-slides">${list.map(c => `<div class="sc-slide">${photo(c.dish, "ph-school", { retry: true })}
        <span class="sc-cap"><b>${c.label}</b> ${esc(c.dish)}</span></div>`).join("")}</div>
      ${list.length > 1 ? `<div class="sc-dots">${list.map((c, i) => `<button class="sc-dot ${i ? "" : "on"}" data-i="${i}" aria-label="Ver ${esc(c.dish)}"></button>`).join("")}</div>` : ""}
    </div>`;
  return `<div class="school-card ${compact ? "compact" : ""}">
    ${slides}
    <div class="sc-body">${compact ? `<div class="sc-row">${photo(s.dishes[0], "ph-sq")}<div class="sc-list">${rows}</div></div>` : rows}
    ${s.note ? `<span class="pill-note">${esc(s.note)}</span>` : ""}</div></div>`;
}
/* Carrusel automático: avanza cada 4 s y se pausa si el usuario lo toca */
let carouselTimers = [];
function startCarousels(root) {
  carouselTimers.forEach(clearInterval);
  carouselTimers = [];
  $$("[data-carousel]", root).forEach(car => {
    const track = $(".sc-slides", car);
    const dots = $$(".sc-dot", car);
    const n = dots.length;
    if (n < 2) return;
    let i = 0, pausedUntil = 0;
    const show = (k, smooth = true) => {
      i = (k + n) % n;
      track.scrollTo({ left: i * track.clientWidth, behavior: smooth ? "smooth" : "auto" });
      dots.forEach((d, j) => d.classList.toggle("on", j === i));
    };
    dots.forEach(d => d.onclick = () => { pausedUntil = Date.now() + 8000; show(Number(d.dataset.i)); });
    track.addEventListener("pointerdown", () => { pausedUntil = Date.now() + 8000; });
    track.addEventListener("scroll", () => {
      const k = Math.round(track.scrollLeft / Math.max(1, track.clientWidth));
      if (k !== i) { i = k; dots.forEach((d, j) => d.classList.toggle("on", j === i)); }
    }, { passive: true });
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduce) carouselTimers.push(setInterval(() => {
      if (!track.isConnected || Date.now() < pausedUntil || document.hidden) return;
      show(i + 1);
    }, 4000));
  });
}

function hintTip(day) {
  const h = day.school?.dinner_hint;
  return h ? `<div class="tip">${ICON.bulb}<span>El cole recomienda para cenar: <b>${esc(h.toLowerCase())}</b></span></div>` : "";
}
function badge(d, deficits) {
  if (!d) return "";
  if (d.source === "cole") return `<span class="badge green">Recomendado por el cole</span>`;
  if (deficits && groupsOf(d).some(g => deficits.includes(g))) return `<span class="badge">Completa la semana</span>`;
  if (d.source === "ia") return `<span class="badge">Idea nueva</span>`;
  if (d.source === "manual") return `<span class="badge">Tu plato</span>`;
  return "";
}

function mealBlock(day, meal, { title, deficits, compact = false } = {}) {
  const p = day[meal];
  if (!p) return "";
  const ch = p.choice;
  const others = (p.options || []).map((o, i) => ({ o, i })).filter(({ o }) => !ch || o.name !== ch.name);
  const outTxt = meal === "cena" ? "Cenamos fuera" : "Comemos fuera";
  const hero = ch
    ? `<div class="hero">${photo(ch.name, compact ? "ph-sq" : "ph-hero", { retry: !compact })}
        ${compact ? "" : `${badge(ch, deficits)}<span class="badge right">${ICON.check}Elegida</span>`}
        <div class="hero-txt"><div class="dish-title">${esc(ch.name)}</div>
        <div class="meta">${esc(groupMeta(ch))}${ch.ingredients?.length ? ` · ${ch.ingredients.length} ingredientes` : ""}</div></div></div>`
    : `<div class="hero out"><div class="ph ph-${compact ? "sq" : "hero"} g-otro"><span class="ph-ico">${ICON.out}</span></div>
        <div class="hero-txt"><div class="dish-title">${outTxt}</div><div class="meta">No entra en la lista de la compra</div></div></div>`;
  const ideas = others.length ? (compact
    ? `<div class="alts-h">O elige otra:</div><div class="alts">${others.map(({ o, i }) => `<button class="alt" data-act="choose" data-date="${day.date}" data-meal="${meal}" data-i="${i}">
        ${photo(o.name, "ph-xs")}<span>${esc(o.name)}</span></button>`).join("")}</div>`
    : `<h3 class="sub-h">${ch ? "Otras ideas" : "Ideas"}</h3>
      <div class="carousel">${others.map(({ o, i }) => `
        <button class="ocard" data-act="choose" data-date="${day.date}" data-meal="${meal}" data-i="${i}" aria-label="Elegir ${esc(o.name)}">
          <div class="oc-photo">${photo(o.name, "ph-card")}${o.source === "cole" ? `<span class="badge green">Cole</span>` : ""}<span class="plus">${ICON.plus}</span></div>
          <span class="oc-name">${esc(o.name)}</span><span class="meta">${esc(groupMeta(o))}</span>
        </button>`).join("")}</div>`) : "";
  return `<section class="meal">
    ${title ? `<h2 class="sec-h">${title}</h2>` : ""}
    ${hero}
    <div class="chips">
      <button class="chip" data-act="regen" data-date="${day.date}" data-meal="${meal}">${ICON.refresh}Más ideas</button>
      <button class="chip" data-act="custom" data-date="${day.date}" data-meal="${meal}">${ICON.pencil}Otro plato</button>
      ${ch ? `<button class="chip" data-act="ings" data-date="${day.date}" data-meal="${meal}">${ICON.list}Ingredientes</button>
              <button class="chip" data-act="clear" data-date="${day.date}" data-meal="${meal}">${ICON.out}${outTxt}</button>` : ""}
    </div>
    <div class="ings-slot" id="ings-${day.date}-${meal}"></div>
    ${ideas}
  </section>`;
}

function bindActions(root) {
  $$("[data-act]", root).forEach(b => b.addEventListener("click", e => {
    const { act, date, meal, i } = b.dataset;
    const btn = e.currentTarget;
    if (act === "choose") return busy(btn, async () => {
      await api(`/api/plan/${date}/${meal}/choose`, { method: "POST", body: { index: Number(i) } });
      await refresh(); toast("Elegido. Ya está en la lista de la compra");
    });
    if (act === "regen") return busy(btn, async () => { await api(`/api/plan/${date}/${meal}/regenerate`, { method: "POST" }); await refresh(); });
    if (act === "clear") return busy(btn, async () => { await api(`/api/plan/${date}/${meal}`, { method: "DELETE" }); await refresh(); toast("Quitado de la lista de la compra"); });
    if (act === "custom") return customDish(date, meal);
    if (act === "ings") return busy(btn, () => toggleIngredients(date, meal, root));
    if (act === "edit-school") return editSchool(date);
  }));
}

async function toggleIngredients(date, meal, root) {
  const slot = $(`#ings-${date}-${meal}`, root);
  if (slot.innerHTML) { slot.innerHTML = ""; return; }
  let d = state.week.days.find(x => x.date === date);
  if (!d[meal].choice.ingredients?.length) {
    state.week = await api(`/api/plan/${date}/${meal}/ingredients`, { method: "POST" });
    d = state.week.days.find(x => x.date === date);
  }
  const ings = d[meal].choice.ingredients || [];
  slot.innerHTML = ings.length
    ? `<ul class="ings">${ings.map(i => `<li><span>${esc(i.name)}</span><b>${esc(i.qty)}</b></li>`).join("")}</ul>`
    : `<p class="help">Este plato no tiene ingredientes guardados. Usa “Otro plato” para añadirlos.</p>`;
}

async function customDish(date, meal) {
  const body = await sheet(`${meal === "cena" ? "Cena" : "Comida"} del ${DOW[wd(date)]} ${fmt(date)}`, `
    <label class="f" for="cd-name">Plato</label>
    <input type="text" id="cd-name" list="recipe-list" placeholder="Ej.: Crema de calabaza y tortilla" autocomplete="off" required>
    <label class="f" for="cd-ings">Ingredientes <span class="muted">(opcional)</span></label>
    <textarea id="cd-ings" placeholder="Uno por línea, con la cantidad tras un guion:&#10;Calabaza - 1 kg&#10;Huevos - 6"></textarea>
    <p class="help">Si eliges un plato de la lista y dejas los ingredientes vacíos, se usan los guardados.</p>`);
  if (!body) return;
  const name = $("#cd-name", body).value.trim();
  if (!name) return;
  const raw = $("#cd-ings", body).value.trim();
  const ingredients = raw ? raw.split("\n").map(l => l.trim()).filter(Boolean).map(l => {
    const [n, ...q] = l.split(/\s+[-–:]\s+/); return { name: n.trim(), qty: q.join(" ").trim(), section: guessSection(n) };
  }) : undefined;
  await busy(null, async () => { await api(`/api/plan/${date}/${meal}/choose`, { method: "POST", body: { name, ingredients } }); await refresh(); toast("Guardado"); });
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
  if (!state.week || !state.week.days.some(x => x.date === date)) state.week = await api(`/api/week?date=${date}`);
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
    await refresh(); toast("Menú corregido");
  });
}

/* =========================================================
   INICIO
   ========================================================= */
async function renderHome() {
  state.after = renderHome;
  const mon = mondayOf(state.date);
  if (!state.week || state.week.monday !== mon || !view.querySelector(".strip")) skeleton();
  const data = state.week = await api(`/api/week?date=${state.date}`);
  const day = data.days.find(d => d.date === state.date) || data.days[0];
  const isToday = day.date === today();
  const weekend = day.weekday >= 5;
  const hour = new Date().getHours();
  const greet = hour < 14 ? "Buenos días" : hour < 21 ? "Buenas tardes" : "Buenas noches";
  const title = weekend ? "Menú del finde" : isToday ? "¿Qué cenamos hoy?" : `${cap(DOW[day.weekday])} ${parse(day.date).getDate()}`;
  const hasMenu = data.days.some(d => d.school && d.school.dishes.length);

  const strip = data.days.map(d => `<button class="dchip ${d.date === day.date ? "sel" : ""} ${d.date === today() ? "today" : ""} ${d.weekday >= 5 ? "weekend" : ""}" data-day="${d.date}" aria-label="${DOW[d.weekday]} ${parse(d.date).getDate()}">
      <span class="dw">${DOW3[d.weekday]}</span><span class="dn">${parse(d.date).getDate()}</span></button>`).join("");

  view.innerHTML = `
    <header class="hero-head">
      <div class="eyebrow">${isToday ? `${greet} · ` : ""}${cap(DOW[day.weekday])}, ${fmt(day.date)}</div>
      <h1>${esc(title)}</h1>
    </header>
    <div class="pill-nav">
      <button class="icon-btn" id="prev" aria-label="Semana anterior">‹</button>
      <button class="pill grow" id="this-week">${ICON.cal}Semana del ${fmt(mon)} al ${fmt(addDays(mon, 6))}</button>
      <button class="icon-btn" id="next" aria-label="Semana siguiente">›</button>
    </div>
    <nav class="strip" aria-label="Días de la semana">${strip}</nav>
    <div id="install-slot"></div>
    ${hasMenu ? "" : `<div class="banner orange"><div class="txt"><b>Aún no hay menú del cole</b>
      El cole lo publica entre el día 1 y el 4 de cada mes y la app lo busca sola. También puedes buscarlo ahora.
      <div class="row"><button class="btn sm primary" data-go="settings">Buscar menú</button></div></div></div>`}
    ${weekend ? weekendContent(day, data) : weekdayContent(day)}
  `;

  $("#prev").onclick = () => { state.date = addDays(mon, -7); renderHome(); };
  $("#next").onclick = () => { state.date = addDays(mon, 7); renderHome(); };
  $("#this-week").onclick = () => { state.date = today(); renderHome(); };
  $$("[data-day]").forEach(b => b.onclick = () => { state.date = b.dataset.day; renderHome(); });
  $$("[data-go]").forEach(b => b.onclick = () => go(b.dataset.go));
  bindActions(view);
  startCarousels(view);
  $("#regen-weekend")?.addEventListener("click", e => busy(e.currentTarget, async () => {
    await api(`/api/week/${mon}/weekend`, { method: "POST" }); await renderHome(); toast("Nuevo menú de fin de semana");
  }));
  Install.renderBanner($("#install-slot"));
  refreshShopCount();
}

function weekdayContent(day) {
  return `
    <div class="sec-row"><h2 class="sec-h">En el cole</h2><button class="link muted" data-act="edit-school" data-date="${day.date}">Corregir</button></div>
    <div class="pad">${schoolCard(day)}</div>
    ${hintTip(day)}
    ${day.comida ? mealBlock(day, "comida", { title: "Comida en casa" }) : ""}
    ${day.cena ? mealBlock(day, "cena", { title: "Para cenar" }) : ""}`;
}

function weekendContent(day, data) {
  const missing = data.deficits;
  const chips = Object.entries(data.targets).map(([g, t]) => {
    const n = (data.counts_weekdays || data.counts)[g] || 0;
    return `<span class="bchip ${n < t ? "low" : ""}">${GROUP_LABEL[g]} ${n}/${t}</span>`;
  }).join("");
  return `
    <div class="balance-card">
      <b>De lunes a viernes (cole y cenas)</b>
      <div class="bchips">${chips}</div>
      <span>${missing.length ? `El finde completa lo que falta: <b>${missing.map(g => GROUP_LABEL[g].toLowerCase()).join(", ")}</b>.` : "La semana va equilibrada: el finde mantiene la variedad."}</span>
    </div>
    ${mealBlock(day, "comida", { title: "Comida", deficits: missing })}
    ${mealBlock(day, "cena", { title: "Cena", deficits: missing })}
    <div class="pad" style="margin-top:22px"><button class="btn primary block" id="regen-weekend">Proponer otro menú de finde</button></div>`;
}

/* =========================================================
   MES (calendario + ventana del día)
   ========================================================= */
async function renderMonth() {
  state.after = null;
  const d = parse(state.date);
  const y = state.month?.y ?? d.getFullYear(), m = state.month?.m ?? d.getMonth() + 1;
  state.month = { y, m };
  if (!view.querySelector(".cal")) skeleton();
  const data = await api(`/api/month?year=${y}&month=${m}`);
  const first = wd(data.days[0].date);
  const blanks = Array.from({ length: first }, () => `<div class="cell blank" aria-hidden="true"></div>`).join("");
  const cells = data.days.map(x => {
    const w = wd(x.date), weekend = w >= 5;
    const hol = !weekend && /festivo|no lectivo|vacaciones/i.test(x.note);
    const lunchName = x.dishes[0] || x.plan.comida || "";
    const lunchSchool = !!x.dishes[0];
    const dinner = x.plan.cena || "";
    const full = [];
    if (x.dishes.length) full.push(`<div class="fb"><span class="fl cole">Cole</span>${courses(x.dishes).map(c => `<span class="${c.dessert ? "fd" : c.label === "1.º" ? "fm" : "fs"}">${esc(c.dish)}</span>`).join("")}</div>`);
    else if (x.plan.comida) full.push(`<div class="fb"><span class="fl">Comida</span><span class="fm">${esc(x.plan.comida)}</span></div>`);
    if (dinner) full.push(`<div class="fb"><span class="fl">Cena</span><span class="fm">${esc(dinner)}</span></div>`);
    return `<button class="cell ${weekend ? "we" : ""} ${hol ? "hol" : ""} ${x.date === today() ? "today" : ""}" data-date="${x.date}" aria-label="${DOW[w]} ${parse(x.date).getDate()}">
      <span class="cn">${parse(x.date).getDate()}${hol ? `<em>Festivo</em>` : ""}</span>
      <span class="mini">
        ${lunchName ? `<span class="strip-ph ${lunchSchool ? "cole" : ""}">${photo(lunchName, "ph-strip")}</span>` : ""}
        ${dinner ? `<span class="strip-ph cena">${photo(dinner, "ph-strip")}</span>` : ""}
      </span>
      <span class="full">${full.join("")}</span>
    </button>`;
  }).join("");
  view.innerHTML = `
    <header class="hero-head">
      <div class="eyebrow">${data.menu ? `Menú del cole · ${esc(data.menu.title || "")}` : "Sin menú del cole"}</div>
      <h1><span style="text-transform:capitalize">${MONTHS[m - 1]}</span> ${y}</h1>
    </header>
    <div class="pill-nav">
      <button class="icon-btn" id="mprev" aria-label="Mes anterior">‹</button>
      ${data.menu ? `<a class="pill grow" href="/api/menus/${y}/${m}/pdf" target="_blank" rel="noopener">${ICON.doc}Ver PDF del cole</a>` : `<span class="pill grow">Sin PDF</span>`}
      <button class="icon-btn" id="mnext" aria-label="Mes siguiente">›</button>
    </div>
    <div class="mlist">${monthList(data.days)}</div>
    <div class="cal">${["L","M","X","J","V","S","D"].map((x, i) => `<div class="dow"><b>${["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"][i]}</b><span>${x}</span></div>`).join("")}${blanks}${cells}</div>
    <div class="legend pad">
      <span><i class="lg cole"></i>Comida</span><span><i class="lg cena"></i>Cena</span>
    </div>
    <p class="help pad mhelp">Toca un día para ver el detalle y cambiarlo sin salir del mes.</p>`;
  $("#mprev").onclick = () => { state.month = m === 1 ? { y: y - 1, m: 12 } : { y, m: m - 1 }; renderMonth(); };
  $("#mnext").onclick = () => { state.month = m === 12 ? { y: y + 1, m: 1 } : { y, m: m + 1 }; renderMonth(); };
  $$(".cell[data-date], .mrow[data-date]").forEach(b => b.onclick = () => openDay(b.dataset.date));
}

function monthList(days) {
  const weeks = [];
  days.forEach(x => {
    const mon = mondayOf(x.date);
    let w = weeks.find(k => k.mon === mon);
    if (!w) { w = { mon, days: [] }; weeks.push(w); }
    w.days.push(x);
  });
  return weeks.map(w => {
    const last = w.days[w.days.length - 1].date;
    const rows = w.days.map(x => {
      const k = wd(x.date), weekend = k >= 5;
      const hol = !weekend && /festivo|no lectivo|vacaciones/i.test(x.note);
      const blocks = [];
      if (x.dishes.length) {
        blocks.push(`<div class="mb"><span class="ml cole">En el cole</span>${courses(x.dishes).map(c =>
          `<span class="${c.dessert ? "md" : c.label === "1.º" ? "mm" : "ms"}">${esc(c.dish)}</span>`).join("")}</div>`);
      } else if (x.plan.comida) {
        blocks.push(`<div class="mb"><span class="ml">Comida en casa</span><span class="mm">${esc(x.plan.comida)}</span></div>`);
      }
      if (x.plan.cena) blocks.push(`<div class="mb"><span class="ml">Cena en casa</span><span class="mm">${esc(x.plan.cena)}</span></div>`);
      if (!blocks.length) blocks.push(`<span class="md">Sin datos todavía</span>`);
      return `<button class="mrow ${weekend ? "we" : ""} ${x.date === today() ? "today" : ""}" data-date="${x.date}">
        <span class="mdate"><small>${DOW3[k]}</small><b>${parse(x.date).getDate()}</b></span>
        <span class="mbody">${hol ? `<span class="pill-note">${esc(x.note || "Festivo")}</span>` : ""}${blocks.join("")}</span>
        <span class="mchev" aria-hidden="true">›</span>
      </button>`;
    }).join("");
    return `<section class="mweek"><h2 class="mweek-h">Semana del ${parse(w.days[0].date).getDate()} al ${fmt(last)}</h2>
      <div class="mweek-box">${rows}</div></section>`;
  }).join("");
}

async function openDay(date) {
  const dlg = $("#daysheet");
  const body = $("#daysheet-body");
  body.innerHTML = `<div class="skeleton" style="margin:0"><i style="height:30px;width:50%"></i><i style="height:120px"></i><i style="height:120px"></i></div>`;
  if (!dlg.open) dlg.showModal();
  dlg.onclick = e => { if (e.target === dlg) dlg.close(); };
  dlg.onclose = () => { state.after = null; if (state.view === "month") renderMonth(); };
  const render = async () => {
    state.week = await api(`/api/week?date=${date}`);
    const day = state.week.days.find(x => x.date === date);
    const weekend = day.weekday >= 5;
    body.innerHTML = `
      <div class="ds-head">
        <div><span class="eyebrow">${cap(MONTHS[parse(date).getMonth()])} ${parse(date).getFullYear()}</span>
        <h2>${cap(DOW[day.weekday])} ${parse(date).getDate()}</h2></div>
        <button class="icon-btn" id="ds-close" aria-label="Cerrar">${ICON.close}</button>
      </div>
      ${day.school?.note ? `<span class="pill-note">${esc(day.school.note)}</span>` : ""}
      ${weekend ? "" : `<div class="ds-block">
        <div class="ds-label"><span class="cole">En el cole</span><button class="link muted" data-act="edit-school" data-date="${date}">Corregir</button></div>
        ${schoolCard(day, { compact: true })}${hintTip(day)}</div>`}
      ${day.comida ? `<div class="ds-block"><div class="ds-label"><span>Comida en casa</span></div>${mealBlock(day, "comida", { compact: true, deficits: weekend ? state.week.deficits : null })}</div>` : ""}
      ${day.cena ? `<div class="ds-block"><div class="ds-label"><span>Cena en casa</span></div>${mealBlock(day, "cena", { compact: true })}</div>` : ""}
      <button class="btn block" id="ds-close2" style="margin-top:16px">Cerrar</button>`;
    $("#ds-close").onclick = () => dlg.close();
    $("#ds-close2").onclick = () => dlg.close();
    bindActions(body);
  };
  state.after = render;
  try { await render(); } catch (e) { body.innerHTML = `<p class="help">${esc(e.message)}</p>`; }
}

/* =========================================================
   COMPRA
   ========================================================= */
async function renderShop() {
  state.after = null;
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
      <span class="pill grow" id="shop-pill">${total - done} por comprar · ${done} en el carro</span>
      <button class="icon-btn" id="snext" aria-label="Semana siguiente">›</button>
    </div>
    <div class="progress" aria-hidden="true"><i style="width:${total ? Math.round(done / total * 100) : 0}%"></i></div>
    <form class="add" id="add">
      <input type="text" id="add-name" placeholder="Añadir algo más…" aria-label="Producto" autocomplete="off">
      <select id="add-sec" aria-label="Sección">${SECTIONS.map(s => `<option ${s === "Otros" ? "selected" : ""}>${s}</option>`).join("")}</select>
      <button class="btn primary sm" aria-label="Añadir">Añadir</button>
    </form>
    ${total ? Object.entries(bySec).map(([sec, items]) => `
      <section class="shop-sec"><h3>${esc(sec)}</h3><ul class="list">
        ${items.map(it => `<li class="row ${it.checked ? "done" : ""}">
          <input type="checkbox" class="check" ${it.checked ? "checked" : ""} data-name="${esc(it.name)}" aria-label="${esc(it.name)}">
          <div class="txt"><div class="t">${esc(it.name)}</div>${it.for.length ? `<div class="s">${esc(it.for.join(" · "))}</div>` : ""}</div>
          ${it.qty ? `<span class="qty">${esc(it.qty)}</span>` : ""}
          <button class="x" data-hide="${esc(it.name)}" aria-label="Quitar ${esc(it.name)}">${ICON.close}</button></li>`).join("")}
      </ul></section>`).join("") : `<div class="empty-state"><b>La lista está vacía</b>Elige cenas y el menú del finde en Inicio y aparecerán aquí sus ingredientes.</div>`}
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
    $("#shop-pill").textContent = `${left} por comprar · ${total - left} en el carro`;
    $(".progress i").style.width = `${Math.round((total - left) / total * 100)}%`;
  });
  $$("[data-hide]").forEach(b => b.onclick = async () => {
    await busy(b, () => api("/api/shopping", { method: "PATCH", body: { date: mon, name: b.dataset.hide, hidden: true } })); reload();
  });
  $("#clear")?.addEventListener("click", async e => { await busy(e.currentTarget, () => api("/api/shopping/clear-checked", { method: "POST", body: { date: mon } })); reload(); });
  $("#share")?.addEventListener("click", async () => {
    const text = `Compra semana del ${fmt(mon)}\n` + Object.entries(bySec).map(([sec, items]) => {
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
  state.after = null;
  skeleton();
  const s = await api("/api/status");
  const u = s.usage || { cost: 0, budget: 1, images: 0, calls: 0 };
  const pct = Math.min(100, Math.round(u.cost / (u.budget || 1) * 100));
  view.innerHTML = `
    <header class="hero-head"><div class="eyebrow">Configuración</div><h1>Ajustes</h1></header>

    <h2 class="sec-h pad">Instalar la app</h2>
    <div id="install-card"></div>

    <h2 class="sec-h pad">Inteligencia artificial</h2>
    <div class="group">
      <div class="item"><div class="txt"><b>${s.ai ? `Activada (${esc(s.ai)})` : "Sin IA"}</b>
        <span>${s.ai ? "Lee el PDF, propone cenas cuando el recetario no tiene suficientes y ayuda a encontrar la foto correcta de cada plato." : "Añade OPENAI_API_KEY para leer mejor el PDF y elegir mejor las fotos de los platos."}</span></div></div>
      ${s.ai ? `<div class="item"><div class="txt"><b>Gasto de este mes: ${u.cost.toFixed(2)} $ de ${u.budget.toFixed(2)} $</b>
        <div class="progress" style="margin:8px 0 6px"><i style="width:${pct}%"></i></div>
        <span>${u.calls} consultas. Al llegar al límite la app sigue funcionando con el recetario.</span></div></div>
` : ""}
      <div class="item"><div class="txt"><b>Fotos de platos</b><span>${photoSummary(s.photos)}</span>
        ${(s.photos.ok || 0) ? `<div style="margin-top:8px"><button class="btn sm" id="credits" style="background:var(--bg)">Ver créditos de las fotos</button></div>` : ""}</div></div>
    </div>

    <h2 class="sec-h pad">Menú del cole</h2>
    <div class="group">
      <div class="item"><div class="txt"><b>Web del comedor</b><span><a href="${esc(s.source)}" target="_blank" rel="noopener">${esc(s.source.replace(/^https?:\/\//, ""))}</a></span></div></div>
      <div class="item"><div class="txt"><b>Última revisión</b><span>${esc(s.last_check || "todavía no")}${s.last_check_result ? ` · ${esc(s.last_check_result)}` : ""}</span></div></div>
      <div class="item" style="gap:8px;flex-wrap:wrap">
        <button class="btn primary" id="fetch">Buscar el menú ahora</button>
        <button class="btn" id="refetch" style="background:var(--bg)">Volver a importar</button>
      </div>
    </div>

    <h2 class="sec-h pad">Subir el PDF a mano</h2>
    <div class="group"><form id="up" class="item" style="flex-wrap:wrap">
      <input type="file" accept="application/pdf" id="pdf" required style="flex:1;min-width:0">
      <button class="btn primary sm">Importar</button></form></div>

    <h2 class="sec-h pad">Menús importados</h2>
    <div class="group">${s.menus.length ? s.menus.map(m => `
      <a class="item" href="/api/menus/${m.year}/${m.month}/pdf" target="_blank" rel="noopener" style="text-decoration:none">
        <div class="txt"><b style="text-transform:capitalize">${MONTHS[m.month - 1]} ${m.year}</b><span>${esc(m.title || "")} · ${m.parser === "ia" ? "leído con IA" : "lector automático"} · ${esc(m.fetched_at)}</span></div><span>›</span></a>`).join("")
      : `<div class="item"><div class="txt">Ninguno todavía</div></div>`}</div>

    <h2 class="sec-h pad">Registro</h2>
    <div class="group"><ul class="logs">${s.logs.map(l => `<li class="${l.level}">${esc(l.at)} · ${esc(l.message)}</li>`).join("") || "<li>Sin actividad</li>"}</ul></div>
    ${s.auth ? `<div class="pad"><a class="btn block" href="/logout">Cerrar sesión</a></div>` : ""}`;

  Install.renderCard($("#install-card"));
  $("#credits")?.addEventListener("click", async () => {
    const r = await api("/api/photo-credits");
    sheet("Créditos de las fotos", r.credits.length
      ? `<ul class="ings" style="margin:8px 0 0">${r.credits.map(c => `<li><span>${esc(c.name)}</span><b>${c.credit_url ? `<a href="${esc(c.credit_url)}" target="_blank" rel="noopener">${esc(c.credit)}</a>` : esc(c.credit)}${c.license ? ` · ${esc(c.license)}` : ""}</b></li>`).join("")}</ul>`
      : `<p class="help">Todas las fotos guardadas se han creado con IA.</p>`, { ok: "", cancel: "Cerrar" });
  });
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

function photoSummary(p) {
  if (!p.enabled) return "Desactivadas.";
  const by = p.by_source || {};
  const web = (by.pexels || 0) + (by.wikimedia || 0) + (by.openverse || 0);
  const parts = [`${p.ok || 0} guardadas${by.ia ? ` (${by.ia} creadas con IA)` : ""}`];
  if (p.pending) parts.push(`${p.pending} buscándose`);
  let txt = parts.join(" · ") + ". Se buscan en internet y la IA ayuda a elegir la que muestra el plato. Si una no es correcta, pulsa el botón de recargar sobre la foto.";
  if (!p.pexels) txt += " Para fotos de más calidad, añade una clave gratuita de Pexels (PEXELS_API_KEY).";
  return txt;
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
    if (outcome === "accepted") toast("App instalada");
    return true;
  },
  howTo() {
    if (this.ios()) return `<ol class="steps"><li>Abre esta página en <b>Safari</b>.</li><li>Pulsa ${SHARE_ICON} <b>Compartir</b>.</li><li>Elige <b>Añadir a pantalla de inicio</b> y pulsa <b>Añadir</b>.</li></ol>`;
    if (this.android()) return `<ol class="steps"><li>Abre el menú <b>⋮</b> de Chrome.</li><li>Pulsa <b>Instalar aplicación</b> (o <b>Añadir a pantalla de inicio</b>).</li></ol>`;
    return `<ol class="steps"><li>En Chrome o Edge, pulsa el icono de <b>instalar</b> de la barra de direcciones.</li><li>En el móvil: Safari → Compartir → Añadir a pantalla de inicio (iPhone) o Chrome → ⋮ → Instalar aplicación (Android).</li></ol>`;
  },
  secureNote() {
    return window.isSecureContext ? "" :
      `<p class="help">Estás entrando por <b>http</b>. En iPhone funciona igual, pero en Android solo se crea un acceso directo. Para la app completa, entra por <b>https</b>.</p>`;
  },
  renderBanner(slot) {
    if (!slot || this.standalone() || this.dismissed()) return;
    if (!this.deferred && !this.ios() && !this.android()) return;
    slot.innerHTML = `<div class="banner green"><div class="txt"><b>Instala Menú familiar</b>
      Tenla en la pantalla de inicio como una app más.
      <div class="row"><button class="btn sm primary" id="inst-go">${this.deferred ? "Instalar" : "Cómo instalar"}</button></div></div>
      <button class="close" id="inst-x" aria-label="Cerrar">${ICON.close}</button></div>`;
    $("#inst-x", slot).onclick = () => { this.dismiss(); slot.innerHTML = ""; };
    $("#inst-go", slot).onclick = async () => { if (!(await this.prompt())) this.showHelp(); else slot.innerHTML = ""; };
  },
  renderCard(el) {
    if (this.standalone()) {
      el.innerHTML = `<div class="group"><div class="item"><div class="txt"><b>Ya estás usando la app instalada</b><span>Se actualiza sola cuando hay versión nueva.</span></div></div></div>`;
      return;
    }
    el.innerHTML = `<div class="group"><div class="item" style="align-items:flex-start"><div class="txt">
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
window.addEventListener("appinstalled", () => { Install.deferred = null; const s = $("#install-slot"); if (s) s.innerHTML = ""; });

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
  RENDER[v]().catch(e => { view.innerHTML = `<div class="empty-state"><b>Algo ha fallado</b>${esc(e.message)}</div>`; });
}
$$(".tabbar button").forEach(b => b.onclick = () => { if (b.dataset.view === "home" && state.view === "home") state.date = today(); go(b.dataset.view); });

(async () => {
  try { const s = await api("/api/status"); state.photos = !!(s.photos && s.photos.enabled); } catch (_) { }
  api("/api/recipes").then(r => { $("#recipe-list").innerHTML = r.recipes.map(x => `<option value="${esc(x.name)}">`).join(""); }).catch(() => {});
  onlineBanner();
  refreshShopCount();
  const initial = location.hash.slice(1);
  go(RENDER[initial] || initial === "week" ? initial : "home");
})();
