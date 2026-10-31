// Panel de datos económicos de EE. UU.
// Este archivo NO contiene cifras: todo se lee de los CSV en la carpeta /data.

const INDICADORES = [
  {
    id: "inflacion",
    titulo: "Inflación",
    archivo: "data/inflacion.csv",
    fuente: "IPC, variación anual · BLS",
    unidad: "%",
    decimales: 1,
    unidadCambio: "pp",
  },
  {
    id: "desempleo",
    titulo: "Desempleo",
    archivo: "data/desempleo.csv",
    fuente: "Tasa de desempleo · BLS",
    unidad: "%",
    decimales: 1,
    unidadCambio: "pp",
  },
  {
    id: "fed",
    titulo: "Tasa de la Fed",
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

function aPuntos(filas, ind) {
  const puntos = filas
    .map((f) => {
      const valor = ind.esRango ? Number(f.superior) : Number(f.valor);
      return {
        periodo: f.periodo,
        etiqueta: f.etiqueta,
        valor,
        inferior: ind.esRango ? Number(f.inferior) : null,
      };
    })
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

function textoValor(p, ind) {
  if (ind.esRango) return `${fmt(p.inferior, ind.decimales)}–${fmt(p.valor, ind.decimales)}`;
  return fmt(p.valor, ind.decimales);
}

function textoCambio(ultimo, anterior, ind) {
  if (!anterior) return "Sin dato anterior para comparar";
  const dif = Math.round((ultimo.valor - anterior.valor) * 1000) / 1000;
  const vs = `frente a ${anterior.etiqueta}`;
  if (dif === 0) return `<span class="flecha">=</span> sin cambio ${vs}`;
  const flecha = dif > 0 ? "▲" : "▼";
  const palabra = dif > 0 ? "sube" : "baja";
  return `<span class="flecha" aria-label="${palabra}">${flecha}</span> ${fmt(Math.abs(dif), ind.decimales)} ${ind.unidadCambio} ${vs}`;
}

// ---------- Tarjeta ----------

function crearTarjeta(ind) {
  const art = document.createElement("article");
  art.className = "tarjeta";
  art.id = `tarjeta-${ind.id}`;
  art.innerHTML = `
    <h2>${ind.titulo}</h2>
    <p class="fuente">${ind.fuente}</p>
    <div class="cuerpo"><p class="error-tarjeta">Cargando…</p></div>`;
  return art;
}

function llenarTarjeta(art, ind, puntos) {
  const ultimo = puntos[puntos.length - 1];
  const anterior = puntos[puntos.length - 2];
  const recientes = puntos.slice(-MESES_EN_GRAFICA);
  const unidad = ind.unidad ? `<span class="unidad">${ind.unidad}</span>` : "";

  const filasTabla = recientes
    .slice()
    .reverse()
    .map((p) => `<tr><td>${p.etiqueta}</td><td>${textoValor(p, ind)}${ind.unidad ? " " + ind.unidad : ""}</td></tr>`)
    .join("");

  art.querySelector(".cuerpo").innerHTML = `
    <p class="valor" data-valor>${textoValor(ultimo, ind)}${unidad}</p>
    <p class="cambio" data-cambio>${textoCambio(ultimo, anterior, ind)}</p>
    <p class="periodo">Último dato: ${ultimo.etiqueta}</p>
    <div class="grafica">
      <div class="cuadro" hidden></div>
    </div>
    <details class="tabla">
      <summary>Ver los números</summary>
      <table><thead><tr><th>Mes</th><th>${ind.esRango ? "Rango" : "Valor"}</th></tr></thead><tbody>${filasTabla}</tbody></table>
    </details>`;

  const cont = art.querySelector(".grafica");
  const dibujar = () => dibujarGrafica(cont, recientes, ind);
  dibujar();
  new ResizeObserver(dibujar).observe(cont);
}

// ---------- Gráfica de líneas (SVG hecho a mano, sin librerías) ----------

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
  const m = { izq: 36, der: 10, arr: 10, aba: 22 };
  const w = ancho - m.izq - m.der;
  const h = alto - m.arr - m.aba;

  cont.querySelector("svg")?.remove();
  const cuadro = cont.querySelector(".cuadro");
  cuadro.hidden = true;

  const valores = puntos.map((p) => p.valor);
  const marcas = marcasEje(Math.min(...valores), Math.max(...valores));
  const yMin = marcas[0];
  const yMax = marcas[marcas.length - 1];
  const x = (i) => m.izq + (puntos.length === 1 ? w / 2 : (i * w) / (puntos.length - 1));
  const y = (v) => m.arr + h - ((v - yMin) / (yMax - yMin || 1)) * h;

  const svg = el("svg", {
    viewBox: `0 0 ${ancho} ${alto}`,
    role: "img",
    tabindex: "0",
    "aria-label": `Gráfica de ${ind.titulo}: de ${puntos[0].etiqueta} a ${puntos[puntos.length - 1].etiqueta}. Toca un punto para ver su valor.`,
  });
  cont.insertBefore(svg, cuadro);

  // Rejilla y eje Y
  // Cuántos decimales necesita el eje (con tolerancia para errores mínimos de la computadora)
  const decimalesDe = (v) => [0, 1, 2, 3].find((d) => Math.abs(Math.round(v * 10 ** d) - v * 10 ** d) < 1e-6) ?? 3;
  const dec = Math.max(...marcas.map(decimalesDe));
  for (const v of marcas) {
    el("line", { class: "rejilla", x1: m.izq, x2: ancho - m.der, y1: y(v), y2: y(v) }, svg);
    const t = el("text", { x: m.izq - 6, y: y(v) + 4, "text-anchor": "end" }, svg);
    t.textContent = v.toFixed(dec);
  }
  // Eje X: solo primer y último mes, para que no se encimen
  const etiquetaCorta = (e) => e.replace(/ (\d{2})(\d{2})$/, " $2");
  [0, puntos.length - 1].forEach((i, k) => {
    const t = el("text", { x: x(i), y: alto - 4, "text-anchor": k === 0 ? "start" : "end" }, svg);
    t.textContent = etiquetaCorta(puntos[i].etiqueta);
  });

  // Línea y puntos
  const guia = el("line", { class: "guia-vertical", y1: m.arr, y2: m.arr + h, visibility: "hidden" }, svg);
  el("path", { class: "linea", d: puntos.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.valor)}`).join("") }, svg);
  const circulos = puntos.map((p, i) => el("circle", { class: "punto", cx: x(i), cy: y(p.valor), r: 4 }, svg));

  // Interacción: tocar o pasar el dedo/ratón muestra el cuadro del punto más cercano
  let activo = -1;
  function mostrar(i) {
    if (i === activo) return;
    if (activo >= 0) circulos[activo].classList.remove("activo"), circulos[activo].setAttribute("r", 4);
    activo = i;
    if (i < 0) {
      cuadro.hidden = true;
      guia.setAttribute("visibility", "hidden");
      return;
    }
    const p = puntos[i];
    circulos[i].classList.add("activo");
    circulos[i].setAttribute("r", 5.5);
    guia.setAttribute("x1", x(i));
    guia.setAttribute("x2", x(i));
    guia.setAttribute("visibility", "visible");
    const extra = ind.esRango ? `<br>Rango: ${fmt(p.inferior, ind.decimales)}–${fmt(p.valor, ind.decimales)} %` : "";
    cuadro.innerHTML = `${p.etiqueta}<strong>${fmt(p.valor, ind.decimales)}${ind.unidad ? " " + ind.unidad : ""}${ind.esRango ? " (límite superior)" : ""}</strong>${extra}`;
    cuadro.hidden = false;
    const mitad = cuadro.offsetWidth / 2;
    const cx = Math.max(mitad, Math.min(ancho - mitad, x(i)));
    cuadro.style.left = `${cx}px`;
    // Arriba del punto si cabe; si no, abajo
    const top = y(p.valor) - cuadro.offsetHeight - 10;
    cuadro.style.top = `${top >= -8 ? top : y(p.valor) + 12}px`;
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
    if (ev.key === "ArrowRight") mostrar(Math.min(puntos.length - 1, activo + 1));
    else if (ev.key === "ArrowLeft") mostrar(Math.max(0, activo < 0 ? puntos.length - 1 : activo - 1));
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

async function cargarEstado() {
  const nota = document.getElementById("nota-actualizacion");
  try {
    const estado = JSON.parse(await cargarTexto("data/estado.json"));
    nota.textContent = `Última actualización: ${fechaLarga(estado.actualizado)}.`;
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
}

iniciar();
