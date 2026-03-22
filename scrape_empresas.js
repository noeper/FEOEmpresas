const fs = require('fs');
const { chromium } = require('playwright');

const INPUT_PATH = process.argv[2];
const OUTPUT_PATH = process.argv[3];

if (!INPUT_PATH || !OUTPUT_PATH) {
  console.error('Usage: node scrape_empresas.js <input.json> <output.json>');
  process.exit(1);
}

const MAX_BODY_CHARS = 9000;
const MAX_DESCRIPTION_LENGTH = 400;
const MAX_PAGES_PER_COMPANY = 3;
const CONCURRENCY = 4;

const TECHNOLOGY_PATTERNS = [
  ['JavaScript', /\bjavascript\b/i],
  ['TypeScript', /\btypescript\b/i],
  ['React', /\breact\b/i],
  ['Angular', /\bangular\b/i],
  ['Vue', /\bvue(?:\.js)?\b/i],
  ['Node.js', /\bnode(?:\.js)?\b/i],
  ['PHP', /\bphp\b/i],
  ['WordPress', /\bwordpress\b/i],
  ['Drupal', /\bdrupal\b/i],
  ['Laravel', /\blaravel\b/i],
  ['Python', /\bpython\b/i],
  ['Java', /\bjava\b/i],
  ['.NET', /\b\.net\b|\bdotnet\b|\bc#\b/i],
  ['Android', /\bandroid\b/i],
  ['iOS', /\bios\b|\biphone\b|\bipad\b/i],
  ['Flutter', /\bflutter\b/i],
  ['React Native', /\breact native\b/i],
  ['SQL', /\bsql\b/i],
  ['MySQL', /\bmysql\b/i],
  ['PostgreSQL', /\bpostgres(?:ql)?\b/i],
  ['MongoDB', /\bmongodb\b/i],
  ['AWS', /\baws\b|\bamazon web services\b/i],
  ['Azure', /\bazure\b/i],
  ['Google Cloud', /\bgoogle cloud\b|\bgcp\b/i],
  ['Docker', /\bdocker\b/i],
  ['Kubernetes', /\bkubernetes\b|\bk8s\b/i],
  ['Linux', /\blinux\b/i],
  ['Windows Server', /\bwindows server\b/i],
  ['DevOps', /\bdevops\b/i],
  ['Cloud', /\bcloud\b|\bnube\b/i],
  ['Ciberseguridad', /\bciberseguridad\b|\bcybersecurity\b|\bsase\b|\bzero trust\b/i],
  ['IA', /\bia\b|\binteligencia artificial\b|\bartificial intelligence\b|\bmachine learning\b|\bgenerative ai\b|\bgenai\b/i],
  ['Analítica de datos', /\banalytics\b|\bdata\b|\bbig data\b|\bdata platform\b/i],
  ['APIs', /\bapi\b|\bintegraciones\b|\bintegration\b/i],
  ['Microservicios', /\bmicroservices?\b/i],
  ['Biometría', /\bbiometric\w*\b|\bbiometr\w*\b/i],
  ['5G', /\b5g\b/i],
  ['Data Center', /\bdata center\b|\bcentro de datos\b/i],
  ['Redes', /\bnetworking\b|\bredes\b|\bconnectivity\b/i],
  ['SAP', /\bsap\b/i],
  ['Salesforce', /\bsalesforce\b/i],
  ['ERP', /\berp\b/i],
  ['CRM', /\bcrm\b/i],
  ['Ecommerce', /\be-?commerce\b|\btienda online\b/i],
  ['UX/UI', /\bux\b|\bui\b|\bexperiencia de usuario\b/i],
];

const SERVICE_PATTERNS = [
  /\b(desarrollo web|desarrollo de software|desarrollo de aplicaciones|aplicaciones empresariales)\b/i,
  /\b(consultor(?:ia|ía) tecnol(?:o|ó)gica|consultor(?:ia|ía) digital|servicios IT)\b/i,
  /\b(ciberseguridad|cloud|infraestructura|redes|data center)\b/i,
  /\b(datos e ia|data & ai|inteligencia artificial|anal(?:i|í)tica de datos)\b/i,
  /\b(marketing digital|dise(?:n|ñ)o web|e-?commerce|ux\/ui)\b/i,
  /\b(soporte t(?:e|é)cnico|administraci(?:o|ó)n de sistemas|servicios gestionados)\b/i,
];

const DAW_PATTERNS = [
  /\bweb\b/i,
  /\bfrontend\b/i,
  /\bbackend\b/i,
  /\be-?commerce\b/i,
  /\bwordpress\b/i,
  /\bdrupal\b/i,
  /\bcms\b/i,
  /\bux\b/i,
  /\bui\b/i,
  /\bdigital products?\b/i,
  /\bmarketing digital\b/i,
];

const DAM_PATTERNS = [
  /\bsoftware\b/i,
  /\baplicaciones?\b/i,
  /\bmobile\b/i,
  /\bandroid\b/i,
  /\bios\b/i,
  /\bia\b/i,
  /\binteligencia artificial\b/i,
  /\bdatos\b/i,
  /\banalytics\b/i,
  /\berp\b/i,
  /\bcrm\b/i,
  /\bapi\b/i,
  /\bintegraciones\b/i,
];

const ASIR_PATTERNS = [
  /\bcloud\b/i,
  /\bnube\b/i,
  /\bciberseguridad\b/i,
  /\bcybersecurity\b/i,
  /\binfraestructura\b/i,
  /\bnetworking\b/i,
  /\bredes\b/i,
  /\bdata center\b/i,
  /\bsistemas\b/i,
  /\bdevops\b/i,
  /\blinux\b/i,
  /\bwindows server\b/i,
  /\bsoporte\b/i,
  /\bservicios gestionados\b/i,
];

/**
 * Normaliza texto eliminando espacios repetidos.
 * @param {string} value
 * @returns {string}
 */
function cleanText(value) {
  return (value || '').replace(/\s+/g, ' ').trim();
}

/**
 * Normaliza una URL para intentar navegarla con seguridad.
 * @param {string} rawUrl
 * @returns {string}
 */
function normalizeUrl(rawUrl) {
  const value = cleanText(rawUrl);
  if (!value || /^n\/d$/i.test(value)) {
    return '';
  }
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  return `https://${value}`;
}

/**
 * Devuelve frases candidatas a partir de bloques de texto.
 * @param {string[]} chunks
 * @returns {string[]}
 */
function collectSentences(chunks) {
  const text = cleanText(chunks.filter(Boolean).join(' '));
  return text
    .split(/(?<=[.!?])\s+/)
    .map(cleanText)
    .filter((sentence) => sentence.length >= 35 && sentence.length <= 260);
}

/**
 * Extrae tecnologías detectables en el contenido.
 * @param {string} haystack
 * @returns {string[]}
 */
function detectTechnologies(haystack) {
  const found = [];
  for (const [label, pattern] of TECHNOLOGY_PATTERNS) {
    if (pattern.test(haystack)) {
      found.push(label);
    }
  }
  return found.slice(0, 6);
}

/**
 * Calcula el encaje del ciclo formativo a partir del contenido.
 * @param {string} haystack
 * @param {string[]} technologies
 * @returns {string}
 */
function detectCycle(haystack, technologies) {
  const matches = [];
  const checkGroup = (label, patterns) => {
    if (patterns.some((pattern) => pattern.test(haystack))) {
      matches.push(label);
    }
  };

  checkGroup('DAW', DAW_PATTERNS);
  checkGroup('DAM', DAM_PATTERNS);
  checkGroup('ASIR', ASIR_PATTERNS);

  if (!matches.length) {
    if (technologies.some((tech) => ['WordPress', 'Drupal', 'UX/UI', 'Ecommerce', 'React', 'Angular', 'Vue'].includes(tech))) {
      matches.push('DAW');
    }
    if (technologies.some((tech) => ['JavaScript', 'TypeScript', 'Node.js', 'Python', 'Java', '.NET', 'Android', 'iOS', 'Flutter', 'React Native', 'IA', 'Analítica de datos', 'APIs'].includes(tech))) {
      matches.push('DAM');
    }
    if (technologies.some((tech) => ['AWS', 'Azure', 'Google Cloud', 'Docker', 'Kubernetes', 'Linux', 'Windows Server', 'DevOps', 'Cloud', 'Ciberseguridad', 'Data Center', 'Redes'].includes(tech))) {
      matches.push('ASIR');
    }
  }

  return matches.length ? matches.join('/') : 'N/D';
}

/**
 * Selecciona una frase descriptiva sobre el servicio principal.
 * @param {string[]} candidates
 * @param {string} fallback
 * @returns {string}
 */
function selectServiceSentence(candidates, fallback) {
  for (const sentence of candidates) {
    if (SERVICE_PATTERNS.some((pattern) => pattern.test(sentence))) {
      return sentence;
    }
  }
  return fallback;
}

/**
 * Construye una descripción corta con actividad y tecnologías.
 * @param {object} payload
 * @returns {string}
 */
function buildDescription(payload) {
  const serviceSentence = cleanText(payload.serviceSentence || payload.metaDescription || payload.title);
  const technologies = payload.technologies.length
    ? `Usa o trabaja con ${payload.technologies.join(', ')}.`
    : 'No se detectan tecnologías concretas en la web pública.';

  let description = cleanText(`${serviceSentence}. ${technologies}`)
    .replace(/\.\s*\./g, '.')
    .replace(/\s+,/g, ',');

  if (!description || description === '.') {
    description = 'N/D';
  }

  if (description.length <= MAX_DESCRIPTION_LENGTH) {
    return description;
  }

  const shortenedService = cleanText(serviceSentence).slice(0, 220).replace(/[,:;]\s*$/, '');
  description = cleanText(`${shortenedService}. ${technologies}`);
  if (description.length <= MAX_DESCRIPTION_LENGTH) {
    return description;
  }

  return `${description.slice(0, MAX_DESCRIPTION_LENGTH - 1).trimEnd()}…`;
}

/**
 * Obtiene un resumen estructurado de una página.
 * @param {import('playwright').Page} page
 * @returns {Promise<object>}
 */
async function collectPageData(page) {
  return page.evaluate((maxChars) => {
    const clean = (value) => (value || '').replace(/\s+/g, ' ').trim();
    const pickTexts = (selector, limit) => Array.from(document.querySelectorAll(selector))
      .map((node) => clean(node.textContent))
      .filter(Boolean)
      .slice(0, limit);
    const links = Array.from(document.querySelectorAll('a[href]'))
      .map((anchor) => ({
        href: anchor.href,
        text: clean(anchor.textContent),
      }))
      .filter((link) => link.href && link.text);

    return {
      url: location.href,
      title: clean(document.title),
      metaDescription: clean(document.querySelector('meta[name="description"]')?.content || ''),
      headings: pickTexts('h1, h2, h3', 15),
      paragraphs: pickTexts('p, li', 40),
      bodyText: clean(document.body?.innerText || '').slice(0, maxChars),
      links,
    };
  }, MAX_BODY_CHARS);
}

/**
 * Acepta banners de cookies básicos para liberar contenido si aparecen.
 * @param {import('playwright').Page} page
 * @returns {Promise<void>}
 */
async function dismissCookieBanners(page) {
  const labels = ['Accept', 'Aceptar', 'Acepto', 'Allow all', 'Aceptar todo', 'Aceptar todas'];
  for (const label of labels) {
    const button = page.getByRole('button', { name: label, exact: false }).first();
    try {
      if (await button.isVisible({ timeout: 800 })) {
        await button.click({ timeout: 1500 });
        return;
      }
    } catch (error) {
      // Ignore missing or stale buttons.
    }
  }
}

/**
 * Devuelve enlaces candidatos a páginas descriptivas dentro del mismo dominio.
 * @param {object[]} links
 * @param {string} origin
 * @returns {string[]}
 */
function pickSupportPages(links, origin) {
  const patterns = [
    { score: 5, pattern: /about|about-us|quienes-somos|sobre-nosotros|empresa/i },
    { score: 4, pattern: /services|servicios|solutions|soluciones|what-we-do/i },
    { score: 2, pattern: /technology|tecnologia|tecnologías|cloud|cyber|infra|software/i },
    { score: 1, pattern: /products|productos|platform|plataforma/i },
  ];

  const candidates = [];
  for (const link of links) {
    if (!link.href.startsWith(origin)) {
      continue;
    }
    let score = 0;
    for (const entry of patterns) {
      if (entry.pattern.test(link.href) || entry.pattern.test(link.text)) {
        score = Math.max(score, entry.score);
      }
    }
    if (score > 0) {
      candidates.push({ href: link.href, score });
    }
  }
  return [...new Map(candidates.sort((a, b) => b.score - a.score).map((item) => [item.href, item])).keys()]
    .slice(0, MAX_PAGES_PER_COMPANY - 1);
}

/**
 * Navega varias páginas de una empresa y genera el resumen final.
 * @param {import('playwright').Browser} browser
 * @param {object} company
 * @returns {Promise<object>}
 */
async function scrapeCompany(browser, company) {
  const normalizedUrl = normalizeUrl(company.web);
  if (!normalizedUrl) {
    return {
      nombre: company.nombre,
      descripcion: 'N/D',
      ciclo: 'N/D',
      scrape_status: 'missing_url',
    };
  }

  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();
  const visited = [];

  try {
    await page.goto(normalizedUrl, { waitUntil: 'domcontentloaded', timeout: 20000 });
    await dismissCookieBanners(page);

    const primaryData = await collectPageData(page);
    visited.push(primaryData.url);

    const supportPages = pickSupportPages(primaryData.links, new URL(primaryData.url).origin);
    const extraData = [];

    for (const supportUrl of supportPages) {
      try {
        await page.goto(supportUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
        await dismissCookieBanners(page);
        extraData.push(await collectPageData(page));
        visited.push(supportUrl);
      } catch (error) {
        extraData.push({ title: '', metaDescription: '', headings: [], paragraphs: [], bodyText: '' });
      }
    }

    const chunks = [
      primaryData.title,
      primaryData.metaDescription,
      ...primaryData.headings,
      ...primaryData.paragraphs,
      primaryData.bodyText,
      ...extraData.flatMap((item) => [item.title, item.metaDescription, ...item.headings, ...item.paragraphs, item.bodyText]),
    ];
    const haystack = cleanText(chunks.join(' '));
    const technologies = detectTechnologies(haystack);
    const sentences = collectSentences(chunks);
    const serviceSentence = selectServiceSentence(
      sentences,
      cleanText(primaryData.metaDescription || primaryData.headings[0] || primaryData.title || '')
    );

    return {
      nombre: company.nombre,
      descripcion: buildDescription({
        title: primaryData.title,
        metaDescription: primaryData.metaDescription,
        serviceSentence,
        technologies,
      }),
      ciclo: detectCycle(haystack, technologies),
      scrape_status: 'ok',
      paginas_visitadas: visited,
    };
  } catch (error) {
    return {
      nombre: company.nombre,
      descripcion: 'N/D',
      ciclo: 'N/D',
      scrape_status: cleanText(String(error)).slice(0, 180) || 'error',
    };
  } finally {
    await context.close();
  }
}

/**
 * Ejecuta tareas con una concurrencia fija.
 * @param {Array<() => Promise<object>>} tasks
 * @param {number} concurrency
 * @returns {Promise<object[]>}
 */
async function runPool(tasks, concurrency) {
  const results = new Array(tasks.length);
  let nextIndex = 0;

  async function worker() {
    while (true) {
      const currentIndex = nextIndex;
      nextIndex += 1;
      if (currentIndex >= tasks.length) {
        return;
      }
      results[currentIndex] = await tasks[currentIndex]();
    }
  }

  await Promise.all(Array.from({ length: concurrency }, () => worker()));
  return results;
}

/**
 * Punto de entrada del scraping por lotes.
 * @returns {Promise<void>}
 */
async function main() {
  const companies = JSON.parse(fs.readFileSync(INPUT_PATH, 'utf8'));
  const browser = await chromium.launch({ headless: true });

  try {
    const tasks = companies.map((company) => () => scrapeCompany(browser, company));
    const results = await runPool(tasks, CONCURRENCY);
    fs.writeFileSync(OUTPUT_PATH, JSON.stringify(results, null, 2), 'utf8');
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
