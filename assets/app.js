// Panel de datos económicos de EE. UU.
// Este archivo NO contiene cifras: todo se lee de los CSV en la carpeta /data.

const INDICADORES = [
  {
    id: "inflacion",
    titulo: "Inflación al consumidor (IPC)",
    icono: "🛒",
    archivo: "data/inflacion.csv",
    fuente: "CPI y Core CPI, anual (y/y) y mensual (m/m) · BLS",
    unidad: "%",
    decimales: 1,
    unidadCambio: "pp",
    // Segunda línea de la gráfica
    nombre1: "CPI general",
    segunda: { columna: "subyacente", nombre: "CPI subyacente" },
  },
  {
    id: "pce",
    titulo: "Inflación PCE",
    icono: "🧾",
    archivo: "data/pce.csv",
    fuente: "Core PCE y PCE · BEA",
    unidad: "%",
    decimales: 1,
    unidadCambio: "pp",
    // La subyacente es el dato principal; la general es el dato de apoyo
    destacado: true,
    columnas: { valor: "subyacente", valor2: "valor", mensual: "mensual_sub", mensual2: "mensual" },
    nombre1: "PCE subyacente (Core PCE)",
    corto1: "subyacente",
    segunda: { columna: "valor", nombre: "PCE general", corto: "general" },
    explicacion:
      "La subyacente quita comida y energía y es la que más mira la Fed (meta: 2 %). " +
      "La general incluye todo, así que muestra cuánto pesan el petróleo y los alimentos.",
    nombreFuente: "Inflación PCE",
    series: ["PCEPILFE", "PCEPI"],
    nombresSeries: { PCEPILFE: "subyacente", PCEPI: "general" },
  },
  {
    id: "empleo",
    titulo: "Empleo (NFP)",
    icono: "👷",
    archivo: "data/empleo.csv",
    fuente: "Nóminas no agrícolas, empleos creados en el mes · BLS",
    unidad: "mil",
    decimales: 0,
    unidadCambio: "mil",
    conSigno: true,
    barras: true,
  },
  {
    id: "desempleo",
    titulo: "Desempleo",
    icono: "💼",
    archivo: "data/desempleo.csv",
    fuente: "Tasa de desempleo · BLS",
    unidad: "%",
    decimales: 1,
    unidadCambio: "pp",
  },
  {
    id: "fed",
    titulo: "Tasa de la Fed",
    icono: "🏦",
    archivo: "data/fed.csv",
    fuente: "Rango objetivo de fondos federales · Reserva Federal",
    unidad: "%",
    decimales: 2,
    unidadCambio: "pp",
    esRango: true, // la gráfica usa el límite superior
  },
  {
    id: "dolar",
    titulo: "Dólar",
    icono: "💱",
    archivo: "data/dolar.csv",
    fuente: "Índice amplio del dólar (ene 2006 = 100) · Reserva Federal",
    unidad: "",
    decimales: 1,
    unidadCambio: "puntos",
  },
];

const MESES_EN_GRAFICA = 12;

// ---------- Lectura de datos ----------

function leerCSV(texto) {
  const lineas = texto.trim().split(/\r?\n/).filter((l) => l.trim() !== "");
  const columnas = lineas.shift().split(",").map((c) => c.trim());
  return lineas.map((linea) => {
    const celdas = linea.split(",").map((c) => c.trim());
    const fila = {};
    columnas.forEach((col, i) => (fila[col] = celdas[i]));
    return fila;
  });
}

async function cargarTexto(ruta) {
  // "no-cache" para que el teléfono no muestre una versión vieja
  const r = await fetch(ruta, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${ruta}: ${r.status}`);
  return r.text();
}

// Celda vacía = sin dato (no cero)
function numero(texto) {
  return texto === undefined || texto === null || String(texto).trim() === "" ? NaN : Number(texto);
}

function aPuntos(filas, ind) {
  // Qué columna del archivo va en cada lugar (la tarjeta PCE las invierte: subyacente primero)
  const c = { valor: "valor", valor2: ind.segunda?.columna, mensual: "mensual", mensual2: "mensual_sub", ...(ind.columnas || {}) };
  const puntos = filas
    .map((f) => ({
      periodo: f.periodo,
      etiqueta: f.etiqueta,
      valor: ind.esRango ? numero(f.superior) : numero(f[c.valor]),
      inferior: ind.esRango ? numero(f.inferior) : null,
      valor2: ind.segunda ? numero(f[c.valor2]) : NaN,
      // Variación mensual (m/m), si el archivo la trae
      mensual: numero(f[c.mensual]),
      mensual2: numero(f[c.mensual2]),
    }))
    .filter((p) => p.periodo && Number.isFinite(p.valor));
  puntos.sort((a, b) => a.periodo.localeCompare(b.periodo));
  return puntos;
}

// ---------- Formato ----------

function fmt(n, dec) {
  // Redondeo "normal" (120.35 → 120.4); toFixed solo a veces falla por cómo guarda decimales la computadora
  const f = Math.pow(10, dec);
  return (Math.round(n * f + 1e-9 * Math.sign(n)) / f).toFixed(dec);
}

// Número con signo (+/−) si el indicador lo pide, p. ej. empleos creados
function fmtNum(n, ind) {
  const t = fmt(Math.abs(n), ind.decimales);
  if (ind.conSigno) return (n > 0 ? "+" : n < 0 ? "−" : "") + t;
  return n < 0 ? "−" + t : t;
}

function textoValor(p, ind) {
  if (ind.esRango) return `${fmt(p.inferior, ind.decimales)}–${fmt(p.valor, ind.decimales)}`;
  return fmtNum(p.valor, ind);
}

function conUnidad(texto, ind) {
  return ind.unidad ? `${texto} ${ind.unidad}` : texto;
}

function textoCambio(actual, anterior, ind, etiquetaAnterior) {
  if (!Number.isFinite(actual) || !Number.isFinite(anterior)) return "Sin dato anterior para comparar";
  const dif = Math.round((actual - anterior) * 1000) / 1000;
  const vs = etiquetaAnterior ? ` frente a ${etiquetaAnterior}` : "";
  if (dif === 0) return `<span class="flecha">=</span> sin cambio${vs}`;
  const flecha = dif > 0 ? "▲" : "▼";
  const palabra = dif > 0 ? "sube" : "baja";
  return `<span class="flecha" aria-label="${palabra}">${flecha}</span> ${fmt(Math.abs(dif), ind.decimales)} ${ind.unidadCambio}${vs}`;
}

// Texto de la variación mensual: "+0.3 %" o "sin dato"
function textoMensual(v) {
  if (!Number.isFinite(v)) return "sin dato";
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${fmt(Math.abs(v), 1)} %`;
}

// ---------- Tarjeta ----------

function crearTarjeta(ind) {
  const art = document.createElement("article");
  art.className = "tarjeta";
  art.id = `tarjeta-${ind.id}`;
  art.innerHTML = `
    <div class="cabeza">
      <span class="icono" aria-hidden="true">${ind.icono || ""}</span>
      <div>
        <h2>${ind.titulo}</h2>
        <p class="fuente">${ind.fuente}</p>
      </div>
    </div>
    <div class="cuerpo"><p class="error-tarjeta">Cargando…</p></div>`;
  return art;
}

function llenarTarjeta(art, ind, puntos) {
  const ultimo = puntos[puntos.length - 1];
  const anterior = puntos[puntos.length - 2];
  const recientes = puntos.slice(-MESES_EN_GRAFICA);
  const unidad = ind.unidad ? `<span class="unidad">${ind.unidad}</span>` : "";
  const dos = Boolean(ind.segunda);

  let cifras;
  if (ind.destacado) {
    // Dato principal grande (anual + mensual debajo) y dato de apoyo más chico (solo anual)
    const v2 = Number.isFinite(ultimo.valor2) ? conUnidad(fmt(ultimo.valor2, ind.decimales), ind) : "sin dato";
    cifras = `
      <p class="etq"><span class="muestra"></span>${ind.nombre1} · anual (y/y)</p>
      <p class="valor" data-valor>${textoValor(ultimo, ind)}${unidad}</p>
      <p class="cambio" data-cambio>${textoCambio(ultimo.valor, anterior?.valor, ind, anterior?.etiqueta)}</p>
      <p class="mensual" data-mensual>Mensual (m/m): <strong>${textoMensual(ultimo.mensual)}</strong></p>
      <p class="apoyo"><span class="muestra rayada"></span>${ind.segunda.nombre} · anual:
        <strong data-valor2>${v2}</strong>
        <span class="apoyo-cambio" data-cambio2>${textoCambio(ultimo.valor2, anterior?.valor2, ind)}</span></p>
      <p class="explica">${ind.explicacion}</p>
      <p class="periodo">Último dato: ${ultimo.etiqueta}</p>`;
  } else if (dos) {
    // Dos cifras lado a lado: general y subyacente
    const v2 = Number.isFinite(ultimo.valor2) ? fmt(ultimo.valor2, ind.decimales) : "–";
    cifras = `
      <div class="doble">
        <div>
          <p class="etq"><span class="muestra"></span>${ind.nombre1}</p>
          <p class="valor" data-valor>${textoValor(ultimo, ind)}${unidad}</p>
          <p class="cambio" data-cambio>${textoCambio(ultimo.valor, anterior?.valor, ind)}</p>
          <p class="mensual" data-mensual>Mensual (m/m): <strong>${textoMensual(ultimo.mensual)}</strong></p>
        </div>
        <div>
          <p class="etq"><span class="muestra rayada"></span>${ind.segunda.nombre}</p>
          <p class="valor" data-valor2>${v2}${unidad}</p>
          <p class="cambio" data-cambio2>${textoCambio(ultimo.valor2, anterior?.valor2, ind)}</p>
          <p class="mensual" data-mensual2>Mensual (m/m): <strong>${textoMensual(ultimo.mensual2)}</strong></p>
        </div>
      </div>
      <p class="periodo">Número grande: variación anual (y/y) · ${ultimo.etiqueta}. La flecha compara con la anual de ${anterior ? anterior.etiqueta : "el mes anterior"}.</p>`;
  } else {
    cifras = `
      <p class="valor" data-valor>${textoValor(ultimo, ind)}${unidad}</p>
      <p class="cambio" data-cambio>${textoCambio(ultimo.valor, anterior?.valor, ind, anterior?.etiqueta)}</p>
      <p class="periodo">${ind.barras ? "Empleos creados en" : "Último dato:"} ${ultimo.etiqueta}${
        ind.barras && anterior ? ` · ${anterior.etiqueta}: ${conUnidad(fmtNum(anterior.valor, ind), ind)}` : ""
      }</p>`;
  }

  const cabeceraTabla = ind.destacado
    ? `<th>Mes</th><th>Subyacente<br><small>y/y · m/m</small></th><th>General<br><small>y/y</small></th>`
    : dos
    ? `<th>Mes</th><th>${ind.nombre1}<br><small>y/y · m/m</small></th><th>${ind.segunda.nombre}<br><small>y/y · m/m</small></th>`
    : `<th>Mes</th><th>${ind.esRango ? "Rango" : "Valor"}</th>`;
  const filasTabla = recientes
    .slice()
    .reverse()
    .map((p) => {
      if (dos) {
        const mm = (v) => (Number.isFinite(v) ? textoMensual(v).replace(" %", "") : "–");
        const a2 = Number.isFinite(p.valor2) ? conUnidad(fmt(p.valor2, ind.decimales), ind) : "–";
        if (ind.destacado) return `<tr><td>${p.etiqueta}</td><td>${conUnidad(textoValor(p, ind), ind)} · ${mm(p.mensual)}</td><td>${a2}</td></tr>`;
        return `<tr><td>${p.etiqueta}</td><td>${conUnidad(textoValor(p, ind), ind)} · ${mm(p.mensual)}</td><td>${a2} · ${mm(p.mensual2)}</td></tr>`;
      }
      return `<tr><td>${p.etiqueta}</td><td>${conUnidad(textoValor(p, ind), ind)}</td></tr>`;
    })
    .join("");

  art.querySelector(".cuerpo").innerHTML = `
    ${cifras}
    <div class="grafica">
      <div class="cuadro" hidden></div>
    </div>
    <details class="tabla">
      <summary>Ver los números</summary>
      <table><thead><tr>${cabeceraTabla}</tr></thead><tbody>${filasTabla}</tbody></table>
    </details>
    ${ind.nombreFuente ? `<p class="fuente-datos" data-fuente>Cargando la fuente de los datos…</p>` : ""}`;
  if (ind.nombreFuente) mostrarFuente(art, ind);

  const cont = art.querySelector(".grafica");
  const dibujar = () => dibujarGrafica(cont, recientes, ind);
  dibujar();
  new ResizeObserver(dibujar).observe(cont);
}

// ---------- Gráficas (SVG hecho a mano, sin librerías) ----------

const SVG_NS = "http://www.w3.org/2000/svg";
function el(nombre, attrs, padre) {
  const n = document.createElementNS(SVG_NS, nombre);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (padre) padre.appendChild(n);
  return n;
}

function marcasEje(min, max) {
  const rango = max - min || 1;
  const paso0 = rango / 3;
  const mag = Math.pow(10, Math.floor(Math.log10(paso0)));
  const paso = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= paso0);
  const inicio = Math.floor(min / paso) * paso;
  const marcas = [];
  for (let v = inicio; v <= max + paso * 0.001; v += paso) marcas.push(Math.round(v * 1e6) / 1e6);
  if (marcas[marcas.length - 1] < max) marcas.push(marcas[marcas.length - 1] + paso);
  return marcas;
}

function dibujarGrafica(cont, puntos, ind) {
  const ancho = cont.clientWidth;
  if (!ancho) return;
  const alto = 170;
  const m = { izq: 40, der: 10, arr: 10, aba: 22 };
  const w = ancho - m.izq - m.der;
  const h = alto - m.arr - m.aba;
  const dos = Boolean(ind.segunda);
  const barras = Boolean(ind.barras);

  cont.querySelector("svg")?.remove();
  const cuadro = cont.querySelector(".cuadro");
  cuadro.hidden = true;

  const valores = puntos.map((p) => p.valor);
  if (dos) puntos.forEach((p) => Number.isFinite(p.valor2) && valores.push(p.valor2));
  if (barras) valores.push(0); // las barras siempre parten de cero
  const marcas = marcasEje(Math.min(...valores), Math.max(...valores));
  const yMin = marcas[0];
  const yMax = marcas[marcas.length - 1];
  const n = puntos.length;
  // Barras: cada mes ocupa una franja; líneas: los puntos van de borde a borde
  const x = barras
    ? (i) => m.izq + ((i + 0.5) * w) / n
    : (i) => m.izq + (n === 1 ? w / 2 : (i * w) / (n - 1));
  const y = (v) => m.arr + h - ((v - yMin) / (yMax - yMin || 1)) * h;

  const svg = el("svg", {
    viewBox: `0 0 ${ancho} ${alto}`,
    role: "img",
    tabindex: "0",
    "aria-label": `Gráfica de ${ind.titulo}: de ${puntos[0].etiqueta} a ${puntos[n - 1].etiqueta}. Toca un punto para ver su valor.`,
  });
  cont.insertBefore(svg, cuadro);

  // Rejilla y eje Y
  // Cuántos decimales necesita el eje (con tolerancia para errores mínimos de la computadora)
  const decimalesDe = (v) => [0, 1, 2, 3].find((d) => Math.abs(Math.round(v * 10 ** d) - v * 10 ** d) < 1e-6) ?? 3;
  const dec = Math.max(...marcas.map(decimalesDe));
  for (const v of marcas) {
    el("line", { class: v === 0 && barras ? "cero" : "rejilla", x1: m.izq, x2: ancho - m.der, y1: y(v), y2: y(v) }, svg);
    const t = el("text", { x: m.izq - 6, y: y(v) + 4, "text-anchor": "end" }, svg);
    t.textContent = v < 0 ? "−" + Math.abs(v).toFixed(dec) : v.toFixed(dec);
  }
  // Eje X: solo primer y último mes, para que no se encimen
  const etiquetaCorta = (e) => e.replace(/ (\d{2})(\d{2})$/, " $2");
  [0, n - 1].forEach((i, k) => {
    const t = el("text", { x: barras ? x(i) : x(i), y: alto - 4, "text-anchor": barras ? "middle" : k === 0 ? "start" : "end" }, svg);
    t.textContent = etiquetaCorta(puntos[i].etiqueta);
  });

  const guia = el("line", { class: "guia-vertical", y1: m.arr, y2: m.arr + h, visibility: "hidden" }, svg);
  // Con muchos meses, los puntos se ocultan y solo aparece el que tocas
  const radio = n > 24 ? 0 : 4;
  let marcas1 = [];
  let marcas2 = [];

  if (barras) {
    const anchoBarra = Math.max(4, Math.min(28, (w / n) * 0.62));
    marcas1 = puntos.map((p, i) => {
      const y0 = y(0);
      const yv = y(p.valor);
      return el("rect", {
        class: p.valor < 0 ? "barra negativa" : "barra",
        x: x(i) - anchoBarra / 2,
        y: Math.min(y0, yv),
        width: anchoBarra,
        height: Math.max(1, Math.abs(yv - y0)),
        rx: 3,
      }, svg);
    });
  } else {
    const trazo = puntos.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.valor)}`).join("");
    const piso = m.arr + h;
    if (!dos) el("path", { class: "area", d: `${trazo}L${x(n - 1)},${piso}L${x(0)},${piso}Z` }, svg);
    if (dos) {
      // Línea rayada para la subyacente (se distingue sin depender del color)
      let d2 = "";
      let empezar = true;
      puntos.forEach((p, i) => {
        if (!Number.isFinite(p.valor2)) return void (empezar = true);
        d2 += `${empezar ? "M" : "L"}${x(i)},${y(p.valor2)}`;
        empezar = false;
      });
      el("path", { class: "linea linea2", d: d2 }, svg);
    }
    el("path", { class: "linea", d: trazo }, svg);
    if (dos) {
      marcas2 = puntos.map((p, i) =>
        Number.isFinite(p.valor2) ? el("circle", { class: "punto punto2", cx: x(i), cy: y(p.valor2), r: radio }, svg) : null
      );
    }
    marcas1 = puntos.map((p, i) => el("circle", { class: "punto", cx: x(i), cy: y(p.valor), r: radio }, svg));
  }

  // Interacción: tocar o pasar el dedo/ratón muestra el cuadro del punto más cercano
  let activo = -1;
  function marcar(i, si) {
    const a = marcas1[i];
    const b = marcas2[i];
    a.classList.toggle("activo", si);
    if (!barras) a.setAttribute("r", si ? 5.5 : radio);
    if (b) b.classList.toggle("activo", si), b.setAttribute("r", si ? 5 : radio);
  }
  function mostrar(i) {
    if (i === activo) return;
    if (activo >= 0) marcar(activo, false);
    activo = i;
    if (i < 0) {
      cuadro.hidden = true;
      guia.setAttribute("visibility", "hidden");
      return;
    }
    const p = puntos[i];
    marcar(i, true);
    guia.setAttribute("x1", x(i));
    guia.setAttribute("x2", x(i));
    guia.setAttribute("visibility", barras ? "hidden" : "visible");
    let html;
    if (dos) {
      const v2 = Number.isFinite(p.valor2) ? conUnidad(fmt(p.valor2, ind.decimales), ind) : "sin dato";
      const c1 = ind.corto1 || "general";
      const c2 = ind.segunda.corto || "subyacente";
      html = `${p.etiqueta}<strong>${conUnidad(fmt(p.valor, ind.decimales), ind)} <small>${c1} y/y</small></strong>` +
        `<span class="extra">${v2} ${c2} y/y</span>` +
        (ind.destacado
          ? `<span class="extra">m/m ${c1}: ${textoMensual(p.mensual)}</span>`
          : `<span class="extra">m/m: ${textoMensual(p.mensual)} gral. · ${textoMensual(p.mensual2)} sub.</span>`);
    } else {
      const extra = ind.esRango
        ? `<span class="extra">Rango: ${fmt(p.inferior, ind.decimales)}–${fmt(p.valor, ind.decimales)} %</span>`
        : ind.textoExtra ? `<span class="extra">${ind.textoExtra}</span>` : barras ? `<span class="extra">empleos</span>` : "";
      html = `${p.etiqueta}<strong>${ind.prefijo || ""}${conUnidad(fmtNum(p.valor, ind), ind)}${ind.esRango ? " (límite superior)" : ""}</strong>${extra}`;
    }
    cuadro.innerHTML = html;
    cuadro.hidden = false;
    const mitad = cuadro.offsetWidth / 2;
    const alto_c = cuadro.offsetHeight;
    // Arriba del punto (o de la barra) si cabe; si no, al costado, para no tapar el resto de la tarjeta
    const alturaRef = barras ? Math.min(y(0), y(p.valor)) : Math.min(y(p.valor), dos && Number.isFinite(p.valor2) ? y(p.valor2) : Infinity);
    const top = alturaRef - alto_c - 10;
    let cx;
    if (top >= -8) {
      cx = x(i);
      cuadro.style.top = `${top}px`;
    } else {
      cx = x(i) > ancho / 2 ? x(i) - mitad - 14 : x(i) + mitad + 14;
      cuadro.style.top = `${Math.max(-8, Math.min(alto - alto_c - 24, alturaRef - alto_c / 2))}px`;
    }
    cuadro.style.left = `${Math.max(mitad, Math.min(ancho - mitad, cx))}px`;
  }
  function indiceCercano(ev) {
    const r = svg.getBoundingClientRect();
    const px = ((ev.clientX - r.left) / r.width) * ancho;
    let mejor = 0;
    puntos.forEach((_, i) => {
      if (Math.abs(x(i) - px) < Math.abs(x(mejor) - px)) mejor = i;
    });
    return mejor;
  }
  svg.addEventListener("pointerdown", (ev) => mostrar(indiceCercano(ev)));
  svg.addEventListener("pointermove", (ev) => mostrar(indiceCercano(ev)));
  svg.addEventListener("pointerleave", (ev) => {
    if (ev.pointerType === "mouse") mostrar(-1);
  });
  svg.addEventListener("blur", () => mostrar(-1));
  svg.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowRight") mostrar(Math.min(n - 1, activo + 1));
    else if (ev.key === "ArrowLeft") mostrar(Math.max(0, activo < 0 ? n - 1 : activo - 1));
    else if (ev.key === "Escape") mostrar(-1);
    else return;
    ev.preventDefault();
  });
}

// Tocar fuera de una gráfica cierra los cuadros abiertos (útil en el teléfono)
document.addEventListener("pointerdown", (ev) => {
  if (ev.target.closest(".grafica")) return;
  document.querySelectorAll(".grafica svg").forEach((s) => s.dispatchEvent(new Event("blur")));
});

// ---------- Poder de compra del dólar (calculado con el IPC) ----------

const PODER = {
  id: "poder",
  titulo: "Poder de compra del dólar",
  icono: "👛",
  archivo: "data/ipc_indice.csv",
  fuente: "Calculado con el IPC · BLS",
  prefijo: "$",
  unidad: "",
  decimales: 2,
};

const PERIODOS = [
  { id: "1", texto: "1 año", anos: 1 },
  { id: "5", texto: "5 años", anos: 5 },
  { id: "10", texto: "10 años", anos: 10 },
  { id: "2006", texto: "Desde 2006", desde: "2006-01" },
];

// Busca el mes de comparación; si ese mes no tiene dato, usa el más cercano anterior
function puntoBase(puntos, periodo) {
  const ultimo = puntos[puntos.length - 1];
  let objetivo = periodo.desde;
  if (!objetivo) {
    const [a, m] = ultimo.periodo.split("-");
    objetivo = `${Number(a) - periodo.anos}-${m}`;
  }
  if (periodo.desde) {
    const p = puntos.find((p) => p.periodo >= objetivo);
    return p && p.periodo === objetivo ? p : null; // sin ese mes exacto, no se ofrece el botón
  }
  const anteriores = puntos.filter((p) => p.periodo <= objetivo);
  return anteriores[anteriores.length - 1];
}

function calculoPoder(puntos, periodo) {
  const ultimo = puntos[puntos.length - 1];
  const base = puntoBase(puntos, periodo);
  if (!base || base === ultimo) return null;
  return {
    base,
    ultimo,
    costoHoy: (100 * ultimo.valor) / base.valor, // lo que hoy cuesta lo que antes costaba $100
    perdida: (1 - base.valor / ultimo.valor) * 100, // cuánto valor perdió cada dólar
  };
}

function llenarPoder(art, puntos) {
  const disponibles = PERIODOS.filter((p) => calculoPoder(puntos, p));
  if (!disponibles.length) throw new Error("no hay suficiente historial del IPC");
  let elegido = disponibles.find((p) => p.id === "10") || disponibles[disponibles.length - 1];

  const filasTabla = disponibles
    .map((p) => {
      const c = calculoPoder(puntos, p);
      return `<tr><td>${c.base.etiqueta}</td><td>$${fmt(c.costoHoy, 2)}</td><td>${fmt(c.perdida, 1)} %</td></tr>`;
    })
    .join("");

  art.querySelector(".cuerpo").innerHTML = `
    <div class="chips" role="group" aria-label="Comparar con">
      ${disponibles.map((p) => `<button type="button" data-periodo="${p.id}">${p.texto}</button>`).join("")}
    </div>
    <p class="frase" data-frase></p>
    <p class="valor" data-valor></p>
    <p class="cambio" data-cambio></p>
    <p class="periodo" data-periodo-txt></p>
    <div class="grafica">
      <div class="cuadro" hidden></div>
    </div>
    <details class="tabla">
      <summary>Ver los números</summary>
      <table><thead><tr><th>Desde</th><th>Lo que costaba $100, hoy</th><th>Pérdida</th></tr></thead><tbody>${filasTabla}</tbody></table>
    </details>`;

  const cont = art.querySelector(".grafica");
  function mostrarPeriodo() {
    const c = calculoPoder(puntos, elegido);
    art.querySelectorAll(".chips button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.periodo === elegido.id)));
    art.querySelector("[data-frase]").innerHTML = `Lo que costaba <strong>$100</strong> en ${c.base.etiqueta}, hoy cuesta:`;
    art.querySelector("[data-valor]").textContent = `$${fmt(c.costoHoy, 2)}`;
    art.querySelector("[data-cambio]").innerHTML =
      `<span class="flecha" aria-label="baja">▼</span> Cada dólar perdió ${fmt(c.perdida, 1)} % de su poder de compra`;
    art.querySelector("[data-periodo-txt]").textContent = `Último dato del IPC: ${c.ultimo.etiqueta}`;
    // Gráfica: cuánto costaba, mes a mes, lo que al inicio costaba $100
    const serie = puntos
      .filter((p) => p.periodo >= c.base.periodo)
      .map((p) => ({ ...p, valor: (100 * p.valor) / c.base.valor }));
    const ind = { ...PODER, textoExtra: `por lo que en ${c.base.etiqueta} costaba $100` };
    const dibujar = () => dibujarGrafica(cont, serie, ind);
    dibujar();
    cont._dibujar = dibujar;
  }
  art.querySelectorAll(".chips button").forEach((b) =>
    b.addEventListener("click", () => {
      elegido = PERIODOS.find((p) => p.id === b.dataset.periodo);
      mostrarPeriodo();
    })
  );
  mostrarPeriodo();
  new ResizeObserver(() => cont._dibujar && cont._dibujar()).observe(cont);
}

// ---------- Avisos y fecha ----------

function aviso(texto) {
  const d = document.createElement("div");
  d.className = "aviso";
  d.textContent = texto;
  document.getElementById("avisos").appendChild(d);
}

function fechaLarga(iso) {
  const [a, mes, d] = iso.split("-").map(Number);
  const meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  return `${d} de ${meses[mes - 1]} de ${a}`;
}

// estado.json se lee una sola vez y lo usan varias partes de la página
const ESTADO = cargarTexto("data/estado.json").then(JSON.parse);
ESTADO.catch(() => {});

// Debajo de la tabla: de dónde salen los datos, versión revisada y fecha de actualización
async function mostrarFuente(art, ind) {
  const p = art.querySelector("[data-fuente]");
  try {
    const estado = await ESTADO;
    const f = (estado.fuentes || {})[ind.nombreFuente] || {};
    const nombres = ind.nombresSeries || {};
    const series = (f.series || ind.series || [])
      .slice()
      .sort((a, b) => (nombres[a] === "subyacente" ? -1 : nombres[b] === "subyacente" ? 1 : 0))
      .map((x) => (nombres[x] ? `${x} (${nombres[x]})` : x))
      .join(" y ");
    const fechas = Object.values(f.versiones || {}).map((v) => String(v).slice(0, 10)).sort();
    const version = fechas.length ? ` Versión revisada más reciente, publicada en FRED el ${fechaLarga(fechas[fechas.length - 1])}.` : "";
    p.textContent =
      `Fuente: ${f.fuente || "BEA vía FRED (Fed de St. Louis)"}${series ? `, series ${series}` : ""}. ` +
      `Porcentajes calculados con esos índices.${version} ` +
      `Última actualización del panel: ${fechaLarga(estado.actualizado)}.`;
  } catch (e) {
    p.textContent = "Fuente: BEA vía FRED (Fed de St. Louis).";
  }
}

async function cargarEstado() {
  const nota = document.getElementById("nota-actualizacion");
  try {
    const estado = await ESTADO;
    nota.textContent = `Última actualización: ${fechaLarga(estado.actualizado)}.`;
    const chip = document.getElementById("fecha-encabezado");
    if (chip) chip.textContent = `Actualizado el ${fechaLarga(estado.actualizado)}`;
    if (estado.datos_de_ejemplo) {
      aviso("Datos de ejemplo: solo el último dato de cada tarjeta coincide con las cifras de referencia. El historial se reemplazará con cifras oficiales en cuanto se conecte la actualización automática.");
    }
    for (const a of estado.avisos || []) aviso(a);
  } catch (e) {
    nota.textContent = "No se pudo leer la fecha de la última actualización.";
  }
}

// ---------- Arranque ----------

async function iniciar() {
  const zona = document.getElementById("tarjetas");
  cargarEstado();
  await Promise.all(
    INDICADORES.map(async (ind) => {
      const art = crearTarjeta(ind);
      zona.appendChild(art);
      try {
        const puntos = aPuntos(leerCSV(await cargarTexto(ind.archivo)), ind);
        if (!puntos.length) throw new Error("archivo vacío");
        llenarTarjeta(art, ind, puntos);
      } catch (e) {
        // Una tarjeta con problemas no rompe las demás
        art.querySelector(".cuerpo").innerHTML = `<p class="error-tarjeta">No se pudieron cargar los datos de «${ind.titulo}» en este momento. Intenta de nuevo más tarde.</p>`;
        console.error(e);
      }
    })
  );

  const art = crearTarjeta(PODER);
  zona.appendChild(art);
  try {
    const puntos = aPuntos(leerCSV(await cargarTexto(PODER.archivo)), PODER);
    llenarPoder(art, puntos);
  } catch (e) {
    art.querySelector(".cuerpo").innerHTML = `<p class="error-tarjeta">No se pudieron cargar los datos de «${PODER.titulo}» en este momento. Intenta de nuevo más tarde.</p>`;
    console.error(e);
  }
}

iniciar();
