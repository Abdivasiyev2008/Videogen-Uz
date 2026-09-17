/* Protsedural SVG personajlar — har kadr vaqt (t) funksiyasi, deterministik.
   People.create(opts) -> {svg, apply(el, t)}
   opts: {view:'side'|'front', anim:'walk'|'run'|'typing'|'phone'|'idle'|'wave'|'point'|'typing_back'|'sit',
          color, skin, hood, glow, scale, flip, props:true}
   Chizish uslubi: qalin yumaloq chiziqlar (flat personaj). */
window.People = (function () {
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

  // Yon ko'rinish (o'ngga qaragan). Bo'g'imlar: hip(0,0) -> torso -120 -> head; shoulder (0,-105)
  function sideRig(o) {
    const c = o.color, s = o.skin, W = 26, H = 40;
    const arm = (id) => `<g data-j="${id}"><line x1="0" y1="0" x2="0" y2="70" stroke="${c}" stroke-width="${W - 2}" stroke-linecap="round"/>
        <g data-j="${id}f" transform="translate(0,70)"><line x1="0" y1="0" x2="0" y2="62" stroke="${c}" stroke-width="${W - 4}" stroke-linecap="round"/>
        <circle cx="0" cy="66" r="12" fill="${s}"/><g data-j="${id}h" transform="translate(0,66)"></g></g></g>`;
    const leg = (id) => `<g data-j="${id}"><line x1="0" y1="0" x2="0" y2="82" stroke="${c}" stroke-width="${W + 2}" stroke-linecap="round"/>
        <g data-j="${id}s" transform="translate(0,82)"><line x1="0" y1="0" x2="0" y2="80" stroke="${c}" stroke-width="${W}" stroke-linecap="round"/>
        <line x1="-4" y1="84" x2="34" y2="84" stroke="${o.shoe || c}" stroke-width="18" stroke-linecap="round"/></g></g>`;
    const head = o.hood
      ? `<path d="M-52 -2 C-52 -70 52 -70 52 -2 L44 8 L-44 8 Z" fill="${c}"/><circle cx="8" cy="-30" r="${H - 12}" fill="${o.face || '#0a0f18'}"/>`
      : `<circle cx="0" cy="-${H}" r="${H}" fill="${s}"/><path d="M-${H} -${H} A${H} ${H} 0 0 1 ${H} -${H} L${H} -${H - 8} Q0 -${H + 14} -${H} -${H - 8} Z" fill="${o.hair || c}"/>`;
    return `<g data-j="root"><g data-j="hip">
      ${leg('legB')}
      <g data-j="torso">
        <g transform="translate(0,-105)">${arm('armB')}</g>
        <line x1="0" y1="0" x2="0" y2="-120" stroke="${c}" stroke-width="${W + 14}" stroke-linecap="round"/>
        <g data-j="head" transform="translate(0,-120)">${head}</g>
        <g transform="translate(0,-105)">${arm('armF')}</g>
      </g>
      ${leg('legF')}
    </g></g>`;
  }

  // Old ko'rinish (yoki orqa). Qo'llar: rotate musbat = tashqariga.
  function frontRig(o) {
    const c = o.color, s = o.skin, W = 26, H = 42;
    const arm = (id, m) => `<g transform="scale(${m},1)"><g data-j="${id}"><line x1="0" y1="0" x2="0" y2="68" stroke="${c}" stroke-width="${W - 2}" stroke-linecap="round"/>
        <g data-j="${id}f" transform="translate(0,68)"><line x1="0" y1="0" x2="0" y2="60" stroke="${c}" stroke-width="${W - 4}" stroke-linecap="round"/><circle cx="0" cy="64" r="12" fill="${s}"/></g></g></g>`;
    const leg = (id, m) => `<g transform="translate(${22 * m},0)"><g data-j="${id}"><line x1="0" y1="0" x2="0" y2="84" stroke="${c}" stroke-width="${W + 2}" stroke-linecap="round"/>
        <g data-j="${id}s" transform="translate(0,84)"><line x1="0" y1="0" x2="0" y2="78" stroke="${c}" stroke-width="${W}" stroke-linecap="round"/><line x1="-10" y1="84" x2="10" y2="84" stroke="${o.shoe || c}" stroke-width="18" stroke-linecap="round"/></g></g></g>`;
    const head = o.hood
      ? `<path d="M-58 4 C-58 -78 58 -78 58 4 L48 10 L-48 10 Z" fill="${c}"/>${o.back ? '' : `<ellipse cx="0" cy="-26" rx="${H - 14}" ry="${H - 10}" fill="${o.face || '#0a0f18'}"/>`}`
      : `<circle cx="0" cy="-${H}" r="${H}" fill="${s}"/><path d="M-${H} -${H} A${H} ${H} 0 0 1 ${H} -${H} L${H} -${H - 10} Q0 -${H + 12} -${H} -${H - 10} Z" fill="${o.hair || c}"/>`;
    return `<g data-j="root"><g data-j="hip">
      ${leg('legL', -1)}${leg('legR', 1)}
      <g data-j="torso">
        <path d="M-44 0 L44 0 L52 -110 L-52 -110 Z" fill="${c}" stroke="${c}" stroke-width="16" stroke-linejoin="round"/>
        <g transform="translate(-50,-104)">${arm('armL', -1)}</g>
        <g transform="translate(50,-104)">${arm('armR', 1)}</g>
        <g data-j="head" transform="translate(0,-118)">${head}</g>
      </g>
    </g></g>`;
  }

  // ---------- pozalar (gradus; oldinga/tashqariga musbat) ----------
  const P = {
    walk(t, sp) {
      const p = 2 * Math.PI * t * (sp || 1.7), q = p + Math.PI, kn = (x) => -52 * Math.max(0, Math.cos(x));
      return { hipY: -4 * Math.abs(Math.sin(p)), torso: 6, head: 0,
        legF: 30 * Math.sin(p), legFs: kn(p), legB: 30 * Math.sin(q), legBs: kn(q),
        armF: -28 * Math.sin(p), armFf: 40 + 12 * Math.sin(p), armB: -28 * Math.sin(q), armBf: 40 + 12 * Math.sin(q) };
    },
    run(t) { const w = P.walk(t, 2.6); w.torso = 16; w.legF *= 1.5; w.legB *= 1.5; w.armF *= 1.6; w.armB *= 1.6; w.armFf = 80; w.armBf = 80; w.hipY = -10 * Math.abs(Math.sin(2 * Math.PI * t * 2.6)); return w; },
    typing(t) {
      const k = Math.sin(t * 13), k2 = Math.cos(t * 13 + 1);
      return { hipY: 0, torso: 10, head: 6 + 2 * Math.sin(t * 2), legF: 88, legFs: -92, legB: 82, legBs: -86,
        armF: 52 + 2 * k, armFf: 44 + 6 * k, armB: 48 + 2 * k2, armBf: 48 + 6 * k2, sit: true };
    },
    phone(t) {
      return { hipY: 0, torso: 3, head: 20 + 1.5 * Math.sin(t * 1.3), legF: 2, legFs: -2, legB: -3, legBs: 0,
        armF: 38, armFf: 98 + 3 * Math.sin(t * 6), armB: 30, armBf: 105, phone: true };
    },
    idle(t) { const b = Math.sin(t * 1.8); return { hipY: 0, torso: 0, head: 3 * Math.sin(t * 0.9), breath: 1 + 0.012 * b, armL: 4 + 2 * b, armLf: 6, armR: 4 + 2 * b, armRf: 6, legL: 0, legR: 0 }; },
    wave(t) { const i = P.idle(t); i.armR = 150; i.armRf = 40 + 28 * Math.sin(t * 9); i.head = 6; return i; },
    point(t) { const i = P.idle(t); i.armR = 105 + 2 * Math.sin(t * 2); i.armRf = 10; return i; },
    typing_back(t) { const k = Math.sin(t * 12), k2 = Math.cos(t * 12 + 0.8); return { hipY: 0, torso: 0, head: 2 * Math.sin(t * 1.6), breath: 1 + 0.01 * Math.sin(t * 2), armL: 26 + 2 * k, armLf: -62 + 6 * k, armR: 26 + 2 * k2, armRf: -62 + 6 * k2, legL: 0, legR: 0 }; },
    sit(t) { return { hipY: 0, torso: 4, head: 2 * Math.sin(t), legF: 90, legFs: -90, legB: 86, legBs: -88, armF: 30, armFf: 60, armB: 28, armBf: 62, sit: true }; },
  };

  // ---------- qo'llash ----------
  function setJ(el, id, tf) { const g = el.querySelector(`[data-j="${id}"]`); if (g) g.setAttribute('transform', tf); }
  function applySide(el, p) {
    setJ(el, 'hip', `translate(0,${p.hipY || 0})`);
    setJ(el, 'torso', `rotate(${p.torso || 0})`);
    setJ(el, 'head', `translate(0,-120) rotate(${p.head || 0})`);
    setJ(el, 'armF', `rotate(${-(p.armF || 0)})`); setJ(el, 'armFf', `translate(0,70) rotate(${-(p.armFf || 0)})`);
    setJ(el, 'armB', `rotate(${-(p.armB || 0)})`); setJ(el, 'armBf', `translate(0,70) rotate(${-(p.armBf || 0)})`);
    setJ(el, 'legF', `rotate(${-(p.legF || 0)})`); setJ(el, 'legFs', `translate(0,82) rotate(${-(p.legFs || 0)})`);
    setJ(el, 'legB', `rotate(${-(p.legB || 0)})`); setJ(el, 'legBs', `translate(0,82) rotate(${-(p.legBs || 0)})`);
  }
  function applyFront(el, p) {
    setJ(el, 'hip', `translate(0,${p.hipY || 0})`);
    setJ(el, 'torso', `rotate(${p.torso || 0}) scale(1,${p.breath || 1})`);
    setJ(el, 'head', `translate(0,-118) rotate(${p.head || 0})`);
    setJ(el, 'armL', `rotate(${-(p.armL || 0)})`); setJ(el, 'armLf', `translate(0,68) rotate(${-(p.armLf || 0)})`);
    setJ(el, 'armR', `rotate(${-(p.armR || 0)})`); setJ(el, 'armRf', `translate(0,68) rotate(${-(p.armRf || 0)})`);
    setJ(el, 'legL', `rotate(${p.legL || 0})`); setJ(el, 'legR', `rotate(${-(p.legR || 0)})`);
  }

  // props: stol/laptop (typing), telefon (phone)
  function props(o) {
    if (o.anim === 'typing') return `<g transform="translate(60,-10)"><rect x="0" y="0" width="230" height="14" rx="6" fill="${o.prop || '#233'}"/><rect x="200" y="14" width="14" height="150" fill="${o.prop || '#233'}"/><rect x="40" y="-44" width="120" height="44" rx="6" fill="${o.propAccent || '#3ee0ff'}" opacity=".9"/><rect x="30" y="-4" width="140" height="6" rx="3" fill="${o.propAccent || '#3ee0ff'}"/></g>
      <g transform="translate(-30,0)"><rect x="-30" y="0" width="60" height="16" rx="6" fill="${o.prop || '#233'}"/><rect x="-6" y="16" width="12" height="150" fill="${o.prop || '#233'}"/><rect x="-46" y="-150" width="16" height="160" rx="6" fill="${o.prop || '#233'}"/></g>`;
    if (o.anim === 'sit') return `<g transform="translate(-30,0)"><rect x="-30" y="0" width="60" height="16" rx="6" fill="${o.prop || '#233'}"/><rect x="-6" y="16" width="12" height="150" fill="${o.prop || '#233'}"/><rect x="-46" y="-150" width="16" height="160" rx="6" fill="${o.prop || '#233'}"/></g>`;
    return '';
  }

  function create(o) {
    o = Object.assign({ view: 'side', anim: 'walk', color: '#1f2a44', skin: '#f2c9a7', hair: '#2a1a12', scale: 1, flip: false, x: 0, y: 0 }, o);
    if (['idle', 'wave', 'point', 'typing_back'].includes(o.anim)) o.view = 'front';
    if (o.anim === 'typing_back') { o.back = true; o.hood = o.hood !== false; }
    const rig = o.view === 'front' ? frontRig(o) : sideRig(o);
    const phone = o.anim === 'phone' ? `<rect x="-14" y="-40" width="28" height="48" rx="5" fill="${o.propAccent || '#3ee0ff'}" transform="rotate(-20)"/>` : '';
    const glow = o.glow ? `style="filter:drop-shadow(0 0 5px ${o.glow}) drop-shadow(0 0 14px ${o.glow})"` : '';
    // pastki nuqta: oyoq tagi (~ +250). Personaj balandligi ~420 (1x).
    const svg = `<svg class="person" width="${600 * o.scale}" height="${520 * o.scale}" viewBox="-300 -300 600 520" style="position:absolute;left:${o.x}px;top:${o.y}px;overflow:visible;${o.flip ? 'transform:scaleX(-1);' : ''}"><g transform="translate(0,${o.anim === 'typing' || o.anim === 'sit' ? 90 : 55})" ${glow}>${props(o)}${rig.replace('<g data-j="armFh" transform="translate(0,66)"></g>', `<g data-j="armFh" transform="translate(0,66)">${phone}</g>`)}</g></svg>`;
    const poseFn = P[o.anim] || P.idle;
    return { svg, apply(el, t) { const p = poseFn(t + (o.phase || 0)); (o.view === 'front' ? applyFront : applySide)(el, p); } };
  }

  return { create, poses: P };
})();
