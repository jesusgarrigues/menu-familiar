"use strict";
const $ = (s, el = document) => el.querySelector(s);
const view = $("#view");
const MONTHS = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
const DOW = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"];
const SECTIONS = ["Frutería","Carnicería","Pescadería","Huevos y lácteos","Panadería","Despensa","Congelados","Otros"];
const GROUP_LABEL = { pescado: "Pescado", legumbre: "Legumbre", huevo: "Huevo", carne: "Carne", verdura: "Verdura", arroz: "Arroz", pasta: "Pasta" };

const state = { view: "week", date: iso(new Date()), month: null, week: null };

function iso(d) { const z = new Date(d.getTime() - d.getTimezoneOffset() * 60000); return z.toISOString().slice(0, 10); }
function parse(s) { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); }
function addDays(s, n) { const d = parse(s); d.setDate(d.getDate() + n); return iso(d); }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function fmt(s) { const d = parse(s); return `${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)}`; }

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 2600);
}

async function api(path, opts = {}) {
  const o = { headers: {}, ...opts };
  if (o.body && !(o.body instanceof FormData)) { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(o.body); }
  const r = await fetch(path, o);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `Error ${r.status}`);
  return data;
}

async function busy(btn, fn) {
  if (btn) btn.disabled = true;
  try { return await fn(); } catch (e) { toast(e.message); } finally { if (btn) btn.disabled = false; }
}

/* ---------- Diálogo genérico ---------- */
function dialog(title, bodyHtml, { ok = "Guardar" } = {}) {
  const dlg = $("#dlg");
  $("#dlg-title").textContent = title;
  $("#dlg-body").innerHTML = bodyHtml;
  $("#dlg-ok").textContent = ok;
  dlg.showModal();
  return new Promise(res => dlg.addEventListener("close", () => res(dlg.returnValue === "ok" ? $("#dlg-body") : null), { once: true }));
}

/* ---------- Semana ---------- */
async function renderWeek() {
  if (!state.week) view.innerHTML = `<p class="loading">Preparando la semana…</p>`;
  const data = state.week = await api(`/api/week?date=${state.date}`);
  const mon = data.monday, sun = addDays(mon, 6);
  const today = iso(new Date());
  const hasMenu = data.days.some(d => d.school && d.school.dishes.length);
  const weekdays = data.days.slice(0, 5), weekend = data.days.slice(5);

  const balance = Object.entries(data.targets).map(([g, t]) => {
    const n = data.counts[g] || 0;
    return `<span class="chip ${n < t ? "low" : ""}" title="Raciones esta semana / recomendadas"><span class="dot"></span>${GROUP_LABEL[g]} ${n}/${t}</span>`;
  }).join("");

  view.innerHTML = `
    <div class="bar">
      <button class="btn icon" id="prev" aria-label="Semana anterior">‹</button>
      <h2>Semana del ${fmt(mon)}<small>hasta el ${fmt(sun)}</small></h2>
      ${mon !== iso(new Date(Date.now() - ((new Date().getDay() + 6) % 7) * 864e5)) ? `<button class="btn small" id="thisweek">Hoy</button>` : ""}
      <button class="btn icon" id="next" aria-label="Semana siguiente">›</button>
    </div>
    ${hasMenu ? "" : `<div class="notice"><b>No hay menú del cole para esta semana.</b>
      <p>El cole lo publica entre el día 1 y el 4 de cada mes. La app lo busca sola cada pocas horas; también puedes buscarlo ahora o subir el PDF a mano.</p>
      <button class="btn primary small" data-go="settings">Ir a Ajustes</button></div>`}
    <div class="balance" aria-label="Balance de la semana">${balance}</div>
    <div class="days">${weekdays.map(d => dayCard(d, today)).join("")}</div>
    <h3 class="section-title">Fin de semana
      <button class="btn small" id="regen-weekend">Proponer otro menú</button></h3>
    <p class="help" style="margin:-4px 0 12px">${data.deficits.length
      ? `Pensado para completar lo que ha faltado entre semana: <b>${data.deficits.map(g => GROUP_LABEL[g].toLowerCase()).join(", ")}</b>.`
      : "La semana va equilibrada; el finde mantiene la variedad."}</p>
    <div class="days">${weekend.map(d => dayCard(d, today)).join("")}</div>`;

  $("#prev").onclick = () => { state.date = addDays(mon, -7); renderWeek(); };
  $("#next").onclick = () => { state.date = addDays(mon, 7); renderWeek(); };
  $("#thisweek")?.addEventListener("click", () => { state.date = iso(new Date()); renderWeek(); });
  $("#regen-weekend").onclick = e => busy(e.currentTarget, async () => { await api(`/api/week/${mon}/weekend`, { method: "POST" }); await renderWeek(); toast("Nuevo menú de fin de semana"); });
  view.querySelectorAll("[data-go]").forEach(b => b.onclick = () => go(b.dataset.go));
  bindDayActions();
}

function mealBlock(d, meal, title) {
  const p = d[meal];
  if (!p) return "";
  const ch = p.choice;
  const opts = (p.options || []).map((o, i) => {
    const sel = ch && o.name === ch.name;
    if (sel) return "";
    const src = o.source === "cole" ? `<span class="src">cole</span>` : o.source === "ia" ? `<span class="src">IA</span>` : "";
    return `<button class="opt ${sel ? "sel" : ""}" data-act="choose" data-date="${d.date}" data-meal="${meal}" data-i="${i}">${esc(o.name)}${src}</button>`;
  }).join("");
  return `<div class="meal">
    ${title ? `<div class="meal-title">${title}</div>` : ""}
    <div class="choice ${ch ? "" : "out"}">${ch ? esc(ch.name) : "Fuera de casa / sin planificar"}</div>
    ${opts.trim() ? `<div class="alt">${ch ? "O bien:" : "Ideas:"}</div><div class="options">${opts}</div>` : ""}
    <div class="actions">
      <button class="linkbtn" data-act="regen" data-date="${d.date}" data-meal="${meal}">Otras ideas</button>
      <button class="linkbtn" data-act="custom" data-date="${d.date}" data-meal="${meal}">Otro plato</button>
      ${ch ? `<button class="linkbtn" data-act="clear" data-date="${d.date}" data-meal="${meal}">${meal === "cena" ? "Cenamos fuera" : "Comemos fuera"}</button>` : ""}
    </div></div>`;
}

function dayCard(d, today) {
  const wd = d.weekday, isWeekend = wd >= 5, s = d.school;
  let school = "";
  if (!isWeekend) {
    const dishes = s && s.dishes.length ? `<ul class="dishes">${s.dishes.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : `<div class="empty">${s?.note ? "" : "Sin menú del cole"}</div>`;
    const hint = s && s.dinner_hint ? `<div class="hint">El cole recomienda para cenar: <b>${esc(s.dinner_hint)}</b></div>` : "";
    school = `<div class="block school-block">
      <div class="label school">En el cole <button class="linkbtn" data-act="edit-school" data-date="${d.date}">Corregir</button></div>
      ${dishes}${s?.note ? `<span class="note">${esc(s.note)}</span>` : ""}${hint}</div>`;
  }
  const home = isWeekend
    ? `<div class="block"><div class="label home">En casa</div>${mealBlock(d, "comida", "Comida")}${mealBlock(d, "cena", "Cena")}</div>`
    : `${d.comida ? `<div class="block"><div class="label home">Comida en casa</div>${mealBlock(d, "comida")}</div>` : ""}
       ${d.cena ? `<div class="block"><div class="label home">Cena en casa</div>${mealBlock(d, "cena")}</div>` : ""}`;
  return `<article class="day ${isWeekend ? "weekend" : ""} ${d.date === today ? "today" : ""}">
    <div class="day-head"><h3>${DOW[wd]}</h3><span class="date">${fmt(d.date)}</span>${d.date === today ? `<span class="badge">Hoy</span>` : ""}</div>
    ${school}${home}</article>`;
}

function bindDayActions() {
  view.querySelectorAll("[data-act]").forEach(b => b.addEventListener("click", e => {
    const { act, date, meal, i } = b.dataset;
    const btn = e.currentTarget;
    if (act === "choose") return busy(btn, async () => { state.week = await api(`/api/plan/${date}/${meal}/choose`, { method: "POST", body: { index: Number(i) } }); renderWeek(); });
    if (act === "regen") return busy(btn, async () => { await api(`/api/plan/${date}/${meal}/regenerate`, { method: "POST" }); renderWeek(); });
    if (act === "clear") return busy(btn, async () => { await api(`/api/plan/${date}/${meal}`, { method: "DELETE" }); renderWeek(); toast("Quitado de la lista de la compra"); });
    if (act === "custom") return customDish(date, meal);
    if (act === "edit-school") return editSchool(date);
  }));
}

async function customDish(date, meal) {
  const body = await dialog(`${meal === "cena" ? "Cena" : "Comida"} del ${DOW[(parse(date).getDay() + 6) % 7]} ${fmt(date)}`, `
    <label class="f" for="cd-name">Plato</label>
    <input type="text" id="cd-name" list="recipe-list" placeholder="Ej.: Crema de calabaza y tortilla" required>
    <label class="f" for="cd-ings">Ingredientes para la compra <span style="font-weight:400">(opcional)</span></label>
    <textarea id="cd-ings" placeholder="Uno por línea, con cantidad tras un guion:&#10;Calabaza - 1 kg&#10;Huevos - 6"></textarea>
    <p class="help">Si eliges un plato del recetario y dejas esto vacío, se usan sus ingredientes.</p>`);
  if (!body) return;
  const name = $("#cd-name", body).value.trim();
  if (!name) return;
  const raw = $("#cd-ings", body).value.trim();
  const ingredients = raw ? raw.split("\n").map(l => l.trim()).filter(Boolean).map(l => {
    const [n, ...q] = l.split(/\s+[-–:]\s+/); return { name: n.trim(), qty: q.join(" ").trim(), section: guessSection(n) };
  }) : undefined;
  await busy(null, async () => { await api(`/api/plan/${date}/${meal}/choose`, { method: "POST", body: { name, ingredients } }); renderWeek(); toast("Guardado"); });
}

function guessSection(n) {
  const s = n.toLowerCase();
  if (/(merluza|salm[oó]n|bacalao|at[uú]n fresco|gamba|langostino|pescad|sardina|dorada|lubina|calamar|sepia|mejill|almeja|rape|gallo)/.test(s)) return "Pescadería";
  if (/(pollo|pavo|ternera|cerdo|carne|lomo|chorizo|jam[oó]n|salchicha|hamburguesa)/.test(s)) return "Carnicería";
  if (/(huevo|leche|yogur|queso|nata|mantequilla|quesito)/.test(s)) return "Huevos y lácteos";
  if (/(pan|masa|tortillas de trigo)/.test(s)) return "Panadería";
  if (/(arroz|pasta|macarr|espagueti|fideo|lenteja|garbanzo|alubia|aceite|harina|sal|lata|tomate frito|tomate triturado|especia|pimentón|comino|azafr)/.test(s)) return "Despensa";
  if (/(congelad|guisantes congelados)/.test(s)) return "Congelados";
  return "Frutería";
}

async function editSchool(date) {
  const d = state.week.days.find(x => x.date === date);
  const s = d.school || { dishes: [], dinner_hint: "", note: "" };
  const body = await dialog(`Menú del cole · ${DOW[d.weekday]} ${fmt(date)}`, `
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
    renderWeek(); toast("Menú corregido");
  });
}

/* ---------- Mes ---------- */
async function renderMonth() {
  const d = parse(state.date);
  const y = state.month?.y ?? d.getFullYear(), m = state.month?.m ?? d.getMonth() + 1;
  state.month = { y, m };
  view.innerHTML = `<p class="loading">Cargando…</p>`;
  const data = await api(`/api/month?year=${y}&month=${m}`);
  const today = iso(new Date());
  const days = data.days.filter(x => { const wd = (parse(x.date).getDay() + 6) % 7; return wd < 5; });
  const first = (parse(days[0].date).getDay() + 6) % 7;
  const blanks = Array.from({ length: first }, () => `<div class="mcell blank" aria-hidden="true"></div>`).join("");
  const cells = days.map(x => {
    const dishes = x.dishes.slice(0, 2).map((s, i) => `<span class="d ${i ? "d2" : ""}">${esc(s)}</span>`).join("");
    const cena = x.plan?.cena ? `<span class="c">🌙 ${esc(x.plan.cena)}</span>` : "";
    return `<button class="mcell ${x.date === today ? "today" : ""}" data-date="${x.date}">
      <span class="n">${parse(x.date).getDate()}</span>${x.note ? `<span class="d note">${esc(x.note)}</span>` : ""}${dishes || (x.note ? "" : `<span class="d empty">—</span>`)}${cena}</button>`;
  }).join("");
  view.innerHTML = `
    <div class="bar">
      <button class="btn icon" id="mprev" aria-label="Mes anterior">‹</button>
      <h2><span style="text-transform:capitalize">${MONTHS[m - 1]}</span> ${y}<small>${data.menu ? esc(data.menu.title || "Menú del cole") : "Sin menú del cole"}</small></h2>
      ${data.menu ? `<a class="btn small" href="/api/menus/${y}/${m}/pdf" target="_blank" rel="noopener">Ver PDF</a>` : ""}
      <button class="btn icon" id="mnext" aria-label="Mes siguiente">›</button>
    </div>
    <div class="month">${["Lun","Mar","Mié","Jue","Vie"].map(x => `<div class="dow">${x}</div>`).join("")}${blanks}${cells}</div>
    <p class="help" style="margin-top:12px">Toca un día para ver su semana, elegir la cena y corregir el menú.</p>`;
  $("#mprev").onclick = () => { state.month = m === 1 ? { y: y - 1, m: 12 } : { y, m: m - 1 }; renderMonth(); };
  $("#mnext").onclick = () => { state.month = m === 12 ? { y: y + 1, m: 1 } : { y, m: m + 1 }; renderMonth(); };
  view.querySelectorAll(".mcell[data-date]").forEach(b => b.onclick = () => { state.date = b.dataset.date; state.week = null; go("week"); });
}

/* ---------- Compra ---------- */
async function renderShop() {
  view.innerHTML = `<p class="loading">Preparando la lista…</p>`;
  const data = await api(`/api/shopping?date=${state.date}`);
  const mon = data.week;
  const bySec = {};
  data.items.forEach(it => (bySec[it.section] ||= []).push(it));
  const pending = data.items.filter(i => !i.checked).length;
  view.innerHTML = `
    <div class="bar">
      <button class="btn icon" id="sprev" aria-label="Semana anterior">‹</button>
      <h2>Compra · semana del ${fmt(mon)}<small>${pending} por comprar · comidas y cenas en casa</small></h2>
      <button class="btn icon" id="snext" aria-label="Semana siguiente">›</button>
    </div>
    <form class="addrow" id="add">
      <input type="text" id="add-name" placeholder="Añadir algo más (leche, pan…)" aria-label="Producto">
      <select id="add-sec" aria-label="Sección">${SECTIONS.map(s => `<option ${s === "Otros" ? "selected" : ""}>${s}</option>`).join("")}</select>
      <button class="btn primary">Añadir</button>
    </form>
    ${Object.keys(bySec).length ? Object.entries(bySec).map(([sec, items]) => `
      <section class="shop-sec"><h3>${esc(sec)}</h3><ul class="items">
        ${items.map(it => `<li class="item ${it.checked ? "done" : ""}">
          <input type="checkbox" ${it.checked ? "checked" : ""} data-name="${esc(it.name)}" aria-label="${esc(it.name)}">
          <div class="txt"><span class="name">${esc(it.name)}</span> ${it.qty ? `<span class="qty">· ${esc(it.qty)}</span>` : ""}
            ${it.for.length ? `<span class="for">Para: ${esc(it.for.join(", "))}</span>` : ""}</div>
          <button class="x" data-hide="${esc(it.name)}" aria-label="Quitar ${esc(it.name)}">×</button></li>`).join("")}
      </ul></section>`).join("") : `<p class="empty">No hay nada en la lista. Elige cenas y menús del fin de semana en la pestaña Semana.</p>`}
    <div class="bar">
      <button class="btn" id="share">Compartir lista</button>
      <button class="btn ghost" id="clear">Quitar lo comprado</button>
    </div>`;
  const reload = () => renderShop();
  $("#sprev").onclick = () => { state.date = addDays(mon, -7); reload(); };
  $("#snext").onclick = () => { state.date = addDays(mon, 7); reload(); };
  $("#add").onsubmit = async e => {
    e.preventDefault(); const name = $("#add-name").value.trim(); if (!name) return;
    await busy(null, () => api("/api/shopping", { method: "POST", body: { date: mon, name, section: $("#add-sec").value } })); reload();
  };
  view.querySelectorAll("input[type=checkbox]").forEach(cb => cb.onchange = async () => {
    cb.closest(".item").classList.toggle("done", cb.checked);
    await busy(null, () => api("/api/shopping", { method: "PATCH", body: { date: mon, name: cb.dataset.name, checked: cb.checked } }));
  });
  view.querySelectorAll("[data-hide]").forEach(b => b.onclick = async () => {
    await busy(b, () => api("/api/shopping", { method: "PATCH", body: { date: mon, name: b.dataset.hide, hidden: true } })); reload();
  });
  $("#clear").onclick = async e => { await busy(e.currentTarget, () => api("/api/shopping/clear-checked", { method: "POST", body: { date: mon } })); reload(); };
  $("#share").onclick = async () => {
    const text = `Compra semana del ${fmt(mon)}\n` + Object.entries(bySec).map(([sec, items]) =>
      `\n${sec}:\n` + items.filter(i => !i.checked).map(i => `- ${i.name}${i.qty ? ` (${i.qty})` : ""}`).join("\n")).join("\n");
    if (navigator.share) { try { await navigator.share({ title: "Lista de la compra", text }); return; } catch (_) { } }
    try { await navigator.clipboard.writeText(text); toast("Lista copiada"); } catch (_) { toast("No se pudo copiar"); }
  };
}

/* ---------- Ajustes ---------- */
async function renderSettings() {
  view.innerHTML = `<p class="loading">Cargando…</p>`;
  const s = await api("/api/status");
  view.innerHTML = `
    <div class="card">
      <h3>Menú del cole</h3>
      <p>La app revisa la web del cole cada pocas horas y, cuando aparece el PDF del mes (normalmente del 1 al 4), lo descarga y lo convierte en el calendario.</p>
      <dl class="kv">
        <dt>Web</dt><dd><a href="${esc(s.source)}" target="_blank" rel="noopener">${esc(s.source)}</a></dd>
        <dt>Última revisión</dt><dd>${esc(s.last_check || "todavía no")}${s.last_check_result ? ` · ${esc(s.last_check_result)}` : ""}</dd>
        <dt>Lectura del PDF</dt><dd>${s.ai ? `Con IA (${esc(s.ai)})` : "Lector automático sin IA · añade una clave de OpenAI o Anthropic para mayor precisión"}</dd>
      </dl>
      <div class="bar" style="margin-top:12px">
        <button class="btn primary" id="fetch">Buscar el menú ahora</button>
        <button class="btn" id="refetch">Volver a importar</button>
      </div>
    </div>
    <div class="card">
      <h3>Subir el PDF a mano</h3>
      <p>Si la descarga automática falla, descarga el PDF de la web del cole y súbelo aquí.</p>
      <form id="up" class="addrow"><input type="file" accept="application/pdf" id="pdf" required><button class="btn primary">Importar</button></form>
    </div>
    <div class="card">
      <h3>Menús importados</h3>
      ${s.menus.length ? `<ul class="dishes">${s.menus.map(m => `<li><a href="/api/menus/${m.year}/${m.month}/pdf" target="_blank" rel="noopener" style="text-transform:capitalize">${MONTHS[m.month - 1]} ${m.year}</a> · ${esc(m.title || "")} <span class="help">(${m.parser === "ia" ? "IA" : "lector"}, ${esc(m.fetched_at)})</span></li>`).join("")}</ul>` : `<p class="empty">Ninguno todavía.</p>`}
    </div>
    <div class="card">
      <h3>Registro</h3>
      <ul class="logs">${s.logs.map(l => `<li class="${l.level}">${esc(l.at)} · ${esc(l.message)}</li>`).join("") || "<li>Sin actividad</li>"}</ul>
    </div>`;
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

/* ---------- Navegación ---------- */
const RENDER = { week: renderWeek, month: renderMonth, shop: renderShop, settings: renderSettings };
function go(v) {
  state.view = v;
  document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("active", b.dataset.view === v));
  history.replaceState(null, "", `#${v}`);
  RENDER[v]().catch(e => { view.innerHTML = `<div class="notice"><b>Algo ha fallado.</b><p>${esc(e.message)}</p></div>`; });
  window.scrollTo({ top: 0 });
}
document.querySelectorAll(".tabs button").forEach(b => b.onclick = () => go(b.dataset.view));

api("/api/recipes").then(r => { $("#recipe-list").innerHTML = r.recipes.map(x => `<option value="${esc(x.name)}">`).join(""); }).catch(() => {});
go(RENDER[location.hash.slice(1)] ? location.hash.slice(1) : "week");
