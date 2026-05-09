import json
from datetime import date, datetime

from flask import Blueprint, render_template_string

from db_supabase import (
    fetch_chain_links,
    fetch_local_authority_search_times,
    fetch_preferred_surveyors,
    fetch_property_images,
    fetch_sales_pipeline,
)

dashboard_bp = Blueprint("dashboard", __name__)

# ─────────────────────────────────────────────────────────────
#  TEMPLATE
# ─────────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NUVU Sales Progression</title>
<link rel="icon" href="/static/logo.png">
<style>
/* ═══ RESET ═══════════════════════════════════════════════ */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#1B3A5C;--claret:#962D3E;--sage:#4A7C6F;--amber:#D4940A;
  --nuvu-green:#C5D93A;--olive:#2A3A0C;--olive-text:#4A5A1A;
  --page-warm:#F5F3EF;--stone:#8B8680;--stone-dark:#6B6560;
  --track:#EDEAE5;--chip-pend-bg:#EDEAE5;--chip-pend-txt:#A8A39D;
  --off-white:#FAFAFA;--white:#FFFFFF;--muted-bg:#F4F4F4;--border:#E8E8E8;
  --txt:#1A1A1A;--txt-secondary:#777777;--placeholder:#BBBBBB;
  --navy-md:#2a4a6e;--navy-card:#1B3A5C;
  --red:#962D3E;--red-chip:#962D3E;--amber-chip:#D4940A;
  --green:#C5D93A;--green-chip:#C5D93A;--blue:#1B3A5C;
  --txt-mid:#777777;--txt-light:#777777;
  --t:background-color .15s ease;
}
html{font-size:15px;scroll-behavior:smooth}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--page-warm);color:var(--txt);min-height:100vh;font-weight:400}

/* ═══ HERO ════════════════════════════════════════════════ */
.hero{position:relative;width:100%;height:480px;overflow:hidden;background:var(--navy)}
.hero-img{width:100%;height:100%;object-fit:cover;display:block}

/* NUVU badge — top right */
.hero-badge{
  position:absolute;top:28px;right:32px;
  background:rgba(27,58,92,.9);
  border-radius:4px;padding:18px 28px 14px;
  display:flex;flex-direction:column;align-items:center;
  border:1px solid rgba(255,255,255,.1);
}
.hero-badge-top{display:flex;align-items:center;gap:14px}
.hero-badge img{width:48px;height:48px;border-radius:50%}
.hero-badge-top h1{font-size:2rem;font-weight:500;color:var(--white);letter-spacing:12px;line-height:1;margin:0;text-indent:12px}
.hero-badge-strapline{font-size:.6rem;color:var(--claret);text-transform:uppercase;letter-spacing:3px;font-weight:500;margin-top:8px;text-align:center;white-space:nowrap}

/* Stats overlay — Direction C */
.hero-stats{
  position:absolute;bottom:24px;left:50%;transform:translateX(-50%);
  width:calc(100% - 64px);max-width:1400px;
  background:rgba(27,58,92,.92);
  border-radius:4px;
  border:1px solid rgba(255,255,255,.1);
  display:flex;justify-content:center;padding:0;
}
.hs{
  flex:1;min-width:0;max-width:200px;text-align:center;padding:20px 12px;
  border-right:1px solid rgba(255,255,255,.12);
  cursor:pointer;transition:var(--t);
}
.hs:last-child{border-right:none}
.hs:hover{background:rgba(255,255,255,.06);border-radius:4px}
.hs-val{font-size:1.85rem;font-weight:500;color:var(--white);line-height:1;font-variant-numeric:tabular-nums}
.hs-val--warn{color:var(--claret)}
.hs-lbl{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:rgba(255,255,255,.6);margin-top:6px;font-weight:500}

/* ═══ PIPELINE FORECAST ═══════ */
.pipeline-section{
  background:var(--page-warm);padding:24px 20px 32px;
  border-top:1px solid var(--border);border-bottom:1px solid var(--border);
}
.pipe-inner{max-width:1280px;margin:0 auto}
.pipeline-header{
  display:flex;justify-content:space-between;align-items:flex-start;
  gap:16px;margin-bottom:20px;
}
.pipeline-title{font-size:20px;font-weight:700;color:var(--navy);letter-spacing:-.02em}
.pipeline-sub{font-size:13px;color:var(--stone);margin-top:6px;max-width:42rem;line-height:1.45}
.pipe-hint{font-size:12px;color:var(--stone);margin-top:10px;line-height:1.4;max-width:40rem}
.ahead-badge{
  background:rgba(197,217,58,.15);color:var(--olive-text);
  padding:6px 12px;border-radius:4px;font-size:.8rem;font-weight:500;
  display:flex;align-items:center;gap:6px;flex-shrink:0;border:1px solid var(--border);
}
.ahead-badge.caution{
  background:rgba(212,148,10,.12);color:var(--amber);border-color:var(--border);
}
.pipe-kpi-row{
  display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:22px;
}
.pipe-kpi{
  background:var(--page-warm);border:2px solid var(--navy);border-radius:6px;
  padding:14px 16px;
}
.pipe-kpi-lbl{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--stone);font-weight:400;margin-bottom:6px}
.pipe-kpi-val{font-size:1.35rem;font-weight:500;color:var(--navy);line-height:1.1;font-variant-numeric:tabular-nums}
.pipe-kpi-sub{font-size:.8rem;color:var(--stone);margin-top:6px;line-height:1.35}
.pipe-split{
  display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:22px;
}
.pipe-panel{
  background:var(--white);border:2px solid var(--navy);border-radius:6px;
  padding:18px 20px 20px;
}
.pipe-panel-h{font-size:.95rem;font-weight:500;color:var(--txt);margin-bottom:4px}
.pipe-panel-sub{font-size:.8rem;color:var(--txt-secondary);margin-bottom:16px;line-height:1.4}
.pipe-fee-chart{
  display:flex;align-items:flex-end;justify-content:space-between;gap:10px;
  height:180px;padding:12px 8px 0;border-radius:6px;background:var(--muted-bg);
  border:2px solid var(--navy);
}
.pipe-fee-col{
  flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;
  justify-content:flex-end;height:100%;gap:8px;
}
.pipe-fee-bar-wrap{
  width:100%;max-width:48px;height:100%;display:flex;align-items:flex-end;justify-content:center;
}
.pipe-fee-bar{
  width:100%;max-width:44px;border-radius:4px 4px 0 0;background:#1B3A5C;
  min-height:4px;position:relative;transition:opacity .2s;
}
.pipe-fee-bar.pipe-fee-bar--remainder{background:rgba(27,58,92,0.18)}
.pipe-fee-bar:hover{opacity:.88}
.pipe-fee-bar span{
  position:absolute;top:-18px;left:50%;transform:translateX(-50%);
  font-size:.68rem;font-weight:500;white-space:nowrap;
}
.pipe-fee-bar:not(.pipe-fee-bar--remainder) span{color:#fff}
.pipe-fee-bar.pipe-fee-bar--remainder span{color:#1B3A5C}
.pipe-fee-x{font-size:.65rem;font-weight:500;color:var(--txt-secondary);text-align:center;line-height:1.2}
.pipe-funnel-rows{display:flex;flex-direction:column;gap:10px}
.pipe-fun-row{display:flex;align-items:center;gap:12px}
.pipe-fun-lbl{
  flex:0 0 38%;min-width:0;font-size:.8rem;font-weight:500;color:var(--txt);
  line-height:1.25;
}
.pipe-fun-track{
  flex:1;height:22px;background:var(--muted-bg);border-radius:4px;overflow:hidden;
  border:1px solid var(--border);
}
.pipe-fun-fill{
  height:100%;border-radius:4px;background:#1B3A5C;
  min-width:4px;transition:width .35s ease;
}
.pipe-fun-pct{font-size:.72rem;font-weight:500;color:var(--txt-secondary);width:36px;text-align:right;flex-shrink:0}
.pipe-forecast-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.pipe-fc{
  border-radius:6px;padding:18px 20px;border:2px solid var(--navy);
  background:var(--white);
}
.pipe-fc-sage{background:#eef4ef}
.pipe-fc-sage .pipe-fc-h{color:#2d4a38}
.pipe-fc-m1{background:rgba(197,217,58,.12)}
.pipe-fc-m1 .pipe-fc-h{color:#4A5A1A}
.pipe-fc-navy{background:#e9eef7}
.pipe-fc-navy .pipe-fc-h{color:#1B3A5C}
.pipe-fc-amber{background:#fdf6ee}
.pipe-fc-amber .pipe-fc-h{color:#7a4a12}
.pipe-fc-h{font-size:11px;text-transform:uppercase;letter-spacing:.05em;font-weight:500;margin-bottom:10px;color:var(--txt-secondary)}
.pipe-fc-count{font-size:1.75rem;font-weight:500;line-height:1;color:var(--txt)}
.pipe-fc-val{font-size:1rem;font-weight:500;color:var(--olive-text);margin-top:4px}
.pipe-fc-fee{font-size:.82rem;font-weight:500;color:var(--txt-secondary);margin-top:6px}
.pipe-fc-note{font-size:.68rem;color:var(--txt-secondary);margin-top:10px;line-height:1.35}

/* ═══ DASH TABS + LEADERBOARDS ════════════════════════════ */
.dash-tab-toolbar{
  position:sticky;top:0;z-index:100;width:100%;
  background:var(--navy);
  overflow-x:auto;-webkit-overflow-scrolling:touch;
}
.dash-tab-inner{
  width:100%;min-width:min-content;margin:0;padding:0;
  display:flex;flex-wrap:nowrap;align-items:stretch;gap:0;
}
.dash-tab{
  flex:1;min-width:88px;padding:11px 0;font-size:12px;font-weight:500;
  font-family:inherit;color:rgba(255,255,255,.5);background:transparent;border:none;
  cursor:pointer;white-space:nowrap;transition:var(--t);
  text-align:center;text-transform:uppercase;letter-spacing:.02em;
  border-right:1px solid rgba(255,255,255,.1);
}
.dash-tab:last-child{border-right:none}
.dash-tab:hover{background:rgba(255,255,255,.06);color:rgba(255,255,255,.5)}
.dash-tab--active{background:var(--nuvu-green);color:var(--olive);font-weight:600}
.tab-panel{display:none}
.tab-panel.tab-panel--active{display:block}
.lb-wrap{max-width:900px;margin:0 auto;padding:24px 20px 48px}
.lb-header{margin-bottom:6px}
.lb-header h2{font-size:1rem;font-weight:500;color:var(--txt);margin:0}
.lb-header p{font-size:.85rem;color:var(--txt-secondary);margin-top:6px;line-height:1.45}
.lb-metric-note{
  font-size:11px;color:var(--txt-secondary);margin:0 0 22px;line-height:1.45;
  cursor:help;max-width:42rem;
}
.lb-cards{display:flex;flex-direction:column;gap:12px}
.lb-card{
  display:flex;flex-wrap:wrap;align-items:stretch;gap:16px 20px;
  background:var(--white);border:2px solid var(--navy);border-radius:6px;
  padding:14px;
}
.lb-rank-col{
  flex:0 0 48px;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;
  text-align:center;padding-top:2px;
}
.lb-rank-num{font-size:1.2rem;font-weight:500;color:var(--navy);line-height:1;font-variant-numeric:tabular-nums}
.lb-move{font-size:11px;margin-top:6px;font-weight:500;line-height:1.2}
.lb-arr--up{color:var(--nuvu-green)}
.lb-arr--down{color:var(--claret)}
.lb-arr--flat{color:var(--txt-secondary)}
.lb-arr-rest{color:var(--txt-secondary);font-weight:500}
.lb-mid{flex:1;min-width:160px}
.lb-company{font-size:.95rem;font-weight:500;color:var(--navy);line-height:1.25;letter-spacing:-.01em}
.lb-location{font-size:.82rem;color:var(--txt-secondary);margin-top:4px}
.lb-stars{font-size:.85rem;color:var(--amber);margin-top:8px;font-weight:500;font-variant-numeric:tabular-nums}
.lb-metrics{
  flex:0 0 auto;display:grid;grid-template-columns:repeat(2,minmax(100px,1fr));gap:10px 16px;
  min-width:200px;align-content:start;
}
.lb-metric-lbl{font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:var(--txt-secondary);font-weight:400}
.lb-metric-val{font-size:.82rem;font-weight:500;color:var(--txt)}
.lb-pill{
  display:inline-block;margin-top:2px;padding:6px 10px;border-radius:4px;
  font-size:.85rem;font-weight:500;
}
.lb-pill--good{background:rgba(197,217,58,.15);color:var(--olive-text)}
.lb-pill--mid{background:var(--muted-bg);color:var(--txt)}
.lb-pill--warn{background:rgba(150,45,62,.12);color:var(--claret)}
.lb-badge-rec{
  display:inline-block;margin-top:8px;padding:2px 8px;border-radius:4px;
  font-size:10px;font-weight:500;background:var(--claret);color:#fff;
  text-transform:uppercase;letter-spacing:.03em;
}
.portal-dash-card{
  max-width:640px;margin:24px auto 48px;padding:24px 26px;
  background:var(--white);border:2px solid var(--navy);border-radius:6px;
}
.portal-dash-card h2{font-size:1rem;font-weight:500;color:var(--txt);margin:0 0 12px}
.portal-dash-card p{font-size:.88rem;color:var(--txt);line-height:1.55;margin:0 0 12px}
.portal-dash-card__muted{font-size:.82rem;color:var(--txt-secondary)}
.portal-dash-card a.na-cta{margin-top:8px;text-decoration:none}

/* ═══ MAIN CONTENT ════════════════════════════════════════ */
.content{max-width:1280px;margin:0 auto;padding:0 20px 60px}

/* ═══ SECTION HEADERS ═════════════════════════════════════ */
.section-banner{
  display:flex;justify-content:space-between;align-items:center;
  padding:28px 0 20px;
  border-left:4px solid transparent;
  padding-left:20px;margin-left:-24px;
}
.section-banner.stalled-banner{border-left-color:var(--red)}
.section-banner.risk-banner{border-left-color:var(--amber)}
.section-banner.green-banner{border-left-color:var(--nuvu-green)}
.section-banner.blue-banner{border-left-color:var(--blue)}
.section-banner.amber-banner{border-left-color:var(--amber)}
.section-banner-left h2{font-size:1rem;font-weight:500;color:var(--txt);display:flex;align-items:center;gap:10px}
.section-banner-left p{font-size:13px;color:var(--stone);margin-top:2px}

/* Section avg progress bar */
.section-avg{display:flex;align-items:center;gap:12px}
.avg-label{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--txt-secondary);font-weight:400;white-space:nowrap}
.avg-bar-wrap{display:flex;align-items:center;gap:8px}
.avg-bar{width:120px;height:8px;border-radius:4px;background:var(--muted-bg);overflow:hidden;border:1px solid var(--border)}
.avg-bar-fill{height:100%;border-radius:4px;transition:width .4s ease}
.avg-pct{font-size:.85rem;font-weight:500;color:var(--txt);min-width:35px;font-variant-numeric:tabular-nums}

/* ═══ CARD GRID ═══════════════════════════════════════════ */
.card-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:14px;
  margin-bottom:12px;
}

/* ═══ PROPERTY CARD — rich horizontal + photo rail ═══════ */
.rich-card{
  display:flex;flex-direction:row;align-items:stretch;
  background:var(--white);border-radius:6px;overflow:hidden;
  cursor:pointer;transition:var(--t);
  border:2px solid var(--navy);min-width:0;
}
.rich-card:hover{background:rgba(27,58,92,.02)}
.rich-card--attention{border-color:var(--claret)}
.rich-thumb{
  flex:0 0 140px;width:140px;min-height:100%;align-self:stretch;
  position:relative;background:var(--navy);overflow:hidden;flex-shrink:0;
}
.rich-thumb img{
  position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;
}
.rich-thumb-placeholder{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  background:var(--navy);
}
.rich-thumb-ph-logo{width:48px;height:48px;object-fit:contain;opacity:.35}
.rich-col{display:flex;flex-direction:column;flex:1;min-width:0}
.rich-body{flex:1;min-width:0;padding:16px 18px;display:flex;flex-direction:column;gap:0}
.rich-badge{
  display:inline-block;font-size:10px;font-weight:600;letter-spacing:.04em;
  text-transform:uppercase;padding:3px 8px;border-radius:3px;margin-bottom:10px;width:fit-content;max-width:100%;
}
.rich-card--on-track .rich-badge{background:rgba(197,217,58,.15);color:var(--olive-text)}
.rich-card--attention .rich-badge{background:rgba(150,45,62,.12);color:var(--claret)}
.rich-card--exchanged .rich-badge{background:rgba(27,58,92,.12);color:var(--navy)}
.rich-card--default .rich-badge{background:var(--track);color:var(--stone-dark)}
.rich-na-strip{margin-bottom:10px}
.rich-na-action{font-size:12px;color:var(--stone-dark);line-height:1.4;margin-bottom:8px}
.rich-na-cta{display:inline-block;font-size:11px;font-weight:600;color:var(--navy);text-decoration:underline}
.rich-row2{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:12px}
.rich-addrblock{flex:1;min-width:0}
.rich-addr{font-size:15px;font-weight:600;color:var(--txt);letter-spacing:-.02em;line-height:1.3}
.rich-sub{font-size:12px;color:var(--stone);margin-top:4px;line-height:1.35}
.rich-feecol{text-align:right;flex-shrink:0}
.rich-fee{font-size:18px;font-weight:600;color:var(--navy);font-variant-numeric:tabular-nums;line-height:1.2}
.rich-fee-lbl{font-size:10px;color:var(--stone);text-transform:uppercase;margin-top:4px;letter-spacing:.04em}
.rich-prog{margin-bottom:12px}
.rich-prog-track{height:6px;border-radius:3px;background:var(--track);overflow:hidden}
.rich-prog-fill{height:100%;border-radius:3px;min-width:0;transition:width .35s ease}
.rich-prog-fill--on-track{background:var(--nuvu-green)}
.rich-prog-fill--attention,.rich-prog-fill--default{background:var(--claret)}
.rich-prog-fill--exchanged{background:var(--navy)}
.rich-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:4px}
.rich-chip{
  font-size:10.5px;font-weight:500;padding:3px 8px;border-radius:3px;white-space:nowrap;
}
.rich-chip--done{background:var(--navy);color:#fff}
.rich-chip--pending{background:var(--chip-pend-bg);color:var(--chip-pend-txt)}
.rich-card--on-track .rich-chip--current{background:var(--nuvu-green);color:var(--olive)}
.rich-card--attention .rich-chip--current,.rich-card--default .rich-chip--current{background:var(--claret);color:#fff}
.rich-card--exchanged .rich-chip--current{background:var(--navy);color:#fff}
.rich-footer{
  display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:12px;
  border-top:1px solid #F0EDE8;padding-top:10px;margin-top:8px;
}
.rich-foot-left{display:flex;flex-wrap:wrap;align-items:center;gap:16px}
.rich-meta{display:flex;flex-direction:column;gap:2px}
.rich-meta-l{font-size:12px;color:var(--stone-dark)}
.rich-meta-v{font-size:12px;font-weight:600;color:var(--txt)}
.rich-meta-v--ok{color:var(--olive-text)}
.rich-meta-v--warn{color:var(--claret)}
.rich-meta-v--muted{color:var(--stone);font-weight:500}
.rich-chain-pill{
  display:inline-flex;align-items:center;gap:5px;font-size:11px;padding:4px 10px;border-radius:3px;
  background:#F5F3EF;color:var(--stone-dark);
}
.rich-chain-pill svg{flex-shrink:0;opacity:.75}
.rich-neg{display:flex;align-items:center;gap:8px}
.rich-neg-av{
  width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:10px;font-weight:700;color:#fff;flex-shrink:0;
}
.rich-neg-av--on-track,.rich-neg-av--exchanged{background:var(--navy)}
.rich-neg-av--attention{background:var(--claret)}
.rich-neg-av--default{background:var(--sage)}
.rich-neg-nm{font-size:11px;color:var(--stone-dark);max-width:140px}
.dash-section{margin-bottom:24px}
.pc-badge--on-track{background:var(--nuvu-green);color:var(--olive-text)}
.pc-badge--stalled,.pc-badge--at-risk{background:var(--claret);color:#fff}
.pc-badge--exchanged{background:var(--navy);color:#fff}

/* ═══ SHOW MORE ═══════════════════════════════════════════ */
.show-more-btn{
  display:flex;align-items:center;justify-content:center;gap:8px;
  width:100%;padding:12px;margin:8px 0 24px;
  background:var(--white);border:1px dashed var(--border);border-radius:4px;
  color:var(--txt-secondary);font-size:.85rem;font-weight:500;cursor:pointer;
  transition:var(--t);
}
.show-more-btn:hover{border-color:var(--navy);color:var(--navy);background:var(--muted-bg)}
.show-more-btn .sm-chev{display:inline-block;transition:transform .15s ease;font-size:10px;color:var(--txt-secondary)}
.show-more-btn.expanded .sm-chev{transform:rotate(180deg)}
.show-more-panel{display:none;margin-bottom:24px}
.show-more-panel.open{display:block}

/* extra summary (for larger counts) */
.extra-summary{
  display:flex;align-items:center;justify-content:space-between;
  padding:14px;margin-top:12px;
  background:var(--white);border:2px solid var(--navy);border-radius:6px;
  color:var(--txt-secondary);font-size:.85rem;
}
.extra-note{font-size:.78rem;color:var(--txt-secondary)}

/* ═══ MODAL ═══════════════════════════════════════════════ */
.modal-overlay{
  display:none;position:fixed;inset:0;
  background:rgba(0,0,0,.5);
  z-index:2000;align-items:center;justify-content:center;padding:20px;
}
.modal-overlay.open{display:flex}
.modal{
  background:var(--white);border-radius:4px;
  width:100%;max-width:620px;max-height:85vh;overflow-y:auto;
  border:1px solid var(--border);
  color:var(--txt);
}
.modal::-webkit-scrollbar{width:5px}
.modal::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px}

/* modal header */
.m-hdr{padding:16px 18px 0;display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px}
.m-hdr h2{font-size:16px;font-weight:500;letter-spacing:-.01em;color:var(--txt)}
.m-hdr .pc-badge{margin-bottom:0}
.m-hdr .m-loc{font-size:.8rem;color:var(--txt-secondary);margin-top:4px}
.m-price{font-size:1rem;font-weight:500;color:var(--navy);font-variant-numeric:tabular-nums}
.m-close{
  width:auto;height:auto;border-radius:0;
  background:transparent;border:none;
  color:var(--txt-secondary);font-size:1.35rem;line-height:1;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  transition:var(--t);margin-left:10px;flex-shrink:0;padding:4px;
}
.m-close:hover{color:var(--txt)}

/* progress bar */
.m-prog{padding:12px 18px 0}
.m-prog-bar{width:100%;height:6px;border-radius:4px;background:var(--muted-bg);overflow:hidden;border:1px solid var(--border)}
.m-prog-fill{height:100%;border-radius:4px;transition:width .4s ease}
.m-prog-fill.clr-stalled{background:var(--claret)}
.m-prog-fill.clr-at-risk{background:var(--amber)}
.m-prog-fill.clr-on-track{background:var(--nuvu-green)}
.m-prog-fill.clr-exchanged{background:var(--navy)}
.m-prog-labels{display:flex;justify-content:space-between;font-size:10px;color:var(--txt-secondary);margin-top:4px;text-transform:uppercase;letter-spacing:.04em}

/* body */
.m-body{padding:10px 22px 0}
.m-div{border:none;border-top:1px solid var(--border);margin:10px 0}

/* alert */
.m-alert{padding:10px 14px;border-radius:4px;margin-bottom:10px;font-size:.82rem;line-height:1.45;display:flex;gap:8px;align-items:flex-start;border:1px solid var(--border)}
.m-alert-red{background:rgba(150,45,62,.08);color:var(--txt);border-color:rgba(150,45,62,.25)}
.m-alert-amber{background:rgba(212,148,10,.1);color:var(--txt);border-color:rgba(212,148,10,.3)}
.m-alert-green{background:rgba(74,124,111,.1);color:var(--txt);border-color:rgba(74,124,111,.25)}

/* next action */
.m-next{background:var(--muted-bg);border:1px solid var(--border);border-radius:4px;padding:10px 14px;margin-bottom:10px}
.m-next-lbl{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--olive-text);font-weight:500;margin-bottom:3px}
.m-next-txt{font-size:.82rem;color:var(--txt);line-height:1.45}

/* action buttons */
.m-actions{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
.m-btn{flex:1;min-width:100px;padding:9px 12px;border-radius:4px;font-size:.78rem;font-weight:500;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px;transition:var(--t);border:none}
.m-btn-call{background:var(--claret);color:#fff}
.m-btn-call:hover{filter:brightness(.95)}
.m-btn-done{background:var(--nuvu-green);color:var(--olive)}
.m-btn-done:hover{filter:brightness(.95)}
.m-btn-outline{background:var(--white);color:var(--txt);border:1px solid var(--border)}
.m-btn-outline:hover{border-color:var(--navy);color:var(--navy)}

/* milestones */
.m-ms h3{font-size:.95rem;font-weight:500;margin-bottom:8px;color:var(--txt)}
.ms-list{display:flex;flex-direction:column}
.ms-item{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border);font-size:.78rem}
.ms-item:last-child{border-bottom:none}
.ms-ic{width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:.6rem}
.ms-ic.done{background:var(--nuvu-green);color:var(--olive)}
.ms-ic.pending{background:var(--muted-bg);border:2px solid var(--border);color:transparent}
.ms-ic.na{background:var(--muted-bg);color:var(--txt-secondary);font-size:.55rem;font-weight:500}
.ms-lb{color:var(--txt);flex:1}
.ms-lb.done-lb{color:var(--txt-secondary);text-decoration:line-through}
.ms-date{font-size:.7rem;color:var(--txt-secondary);margin-left:auto;white-space:nowrap}
.ms-edit-btn{background:none;border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:.65rem;color:var(--txt-secondary);cursor:pointer;transition:var(--t);flex-shrink:0}
.ms-edit-btn:hover{border-color:var(--navy);color:var(--navy)}
.m-portal-forms{margin-bottom:10px}
.m-portal-forms h3{font-size:.95rem;font-weight:500;margin-bottom:8px;color:var(--txt)}
.portal-form-block{margin-bottom:10px;padding-bottom:8px;border-bottom:1px dashed #e5e7eb}
.portal-form-block:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0}
.portal-line{font-size:.78rem;color:var(--txt);margin-bottom:4px;line-height:1.4}
.portal-line strong{color:var(--txt-secondary);font-weight:500;margin-right:6px}
.portal-line.empty{color:var(--txt-secondary)}
.portal-actions-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:4px;align-items:center}
a.portal-action-link{display:inline-block;font-size:.75rem;font-weight:700;color:var(--navy);text-decoration:underline}
a.portal-action-link:hover{color:var(--claret)}
button.portal-send-btn{font-size:.72rem;font-weight:500;padding:5px 10px;border-radius:4px;border:1px solid var(--border);background:var(--muted-bg);color:var(--txt-secondary);cursor:not-allowed;opacity:.75}
button.portal-send-btn[disabled]{cursor:not-allowed}
a.portal-review-link{display:inline-block;font-size:.75rem;font-weight:700;color:var(--navy);text-decoration:underline}
a.portal-review-link:hover{color:var(--claret)}
.ms-edit-form{display:flex;align-items:center;gap:6px;margin-left:auto;flex-shrink:0}
.ms-edit-form input[type=date]{font-size:.72rem;padding:2px 6px;border:1px solid var(--border);border-radius:4px;color:var(--txt)}
.ms-edit-form button{padding:2px 8px;border-radius:4px;font-size:.65rem;font-weight:500;cursor:pointer;border:none}
.ms-save-btn{background:var(--nuvu-green);color:var(--olive)}
.ms-cancel-btn{background:var(--muted-bg);color:var(--txt-secondary)}
.ms-pending-lb{color:var(--txt-secondary)}

/* note editor */
.note-block{background:var(--muted-bg);border:1px solid var(--border);border-radius:4px;padding:10px 14px;margin-bottom:8px}
.note-block-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.note-block-lbl{font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:var(--txt-secondary);font-weight:400}
.note-edit-btn{background:none;border:1px solid var(--border);border-radius:4px;padding:2px 10px;font-size:.65rem;color:var(--txt-secondary);cursor:pointer;transition:var(--t)}
.note-edit-btn:hover{border-color:var(--navy);color:var(--navy)}
.note-block-txt{font-size:.82rem;line-height:1.5;color:var(--txt);white-space:pre-wrap}
.note-block-txt.empty{color:var(--txt-secondary)}
.note-textarea{width:100%;min-height:60px;font-size:.82rem;font-family:inherit;line-height:1.5;border:1px solid var(--border);border-radius:4px;padding:8px 10px;resize:vertical;color:var(--txt)}
.note-textarea:focus{outline:none;border-color:var(--navy)}
.note-actions{display:flex;gap:6px;margin-top:6px}
.note-save-btn{background:var(--nuvu-green);color:var(--olive);border:none;border-radius:4px;padding:4px 14px;font-size:.72rem;font-weight:600;cursor:pointer}
.note-cancel-btn{background:var(--muted-bg);color:var(--txt-secondary);border:none;border-radius:4px;padding:4px 14px;font-size:.72rem;cursor:pointer}

/* activity notes */
.act-item{background:var(--muted-bg);border:1px solid var(--border);border-radius:4px;padding:8px 12px;margin-bottom:6px;font-size:.8rem;line-height:1.45;color:var(--txt)}
.act-idx{font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:var(--txt-secondary);font-weight:400}

/* expandable details */
.m-det-toggle{
  width:100%;background:var(--muted-bg);border:1px solid var(--border);
  border-radius:4px;padding:10px 14px;margin-bottom:4px;
  color:var(--txt);font-size:.82rem;font-weight:500;cursor:pointer;
  display:flex;align-items:center;justify-content:space-between;transition:var(--t);
}
.m-det-toggle:hover{border-color:var(--navy)}
.m-det-toggle .det-chev{font-size:10px;color:var(--txt-secondary);transition:transform .15s ease}
.m-det-toggle.expanded .det-chev{transform:rotate(180deg)}
.m-det-panel{max-height:0;overflow:hidden;transition:max-height .35s ease}
.m-det-panel.expanded{max-height:650px}
.m-det-inner{padding:14px 0 4px}
.det-grid{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px}
.d-r{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border);font-size:.75rem}
.d-r:last-child{border-bottom:none}
.d-l{color:var(--txt-secondary)}
.d-v{font-weight:500;color:var(--txt);text-align:right}
.d-full{grid-column:1/-1;padding:10px 0 2px}
.d-full-l{font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:var(--txt-secondary);margin-bottom:3px;font-weight:400}
.d-full-v{font-size:.82rem;color:var(--txt);line-height:1.5}

.m-footer{padding:6px 22px 16px}

/* ═══ RESPONSIVE ══════════════════════════════════════════ */
@media(max-width:960px){
  .card-grid{grid-template-columns:repeat(2,1fr)}
  .pipe-kpi-row{grid-template-columns:repeat(2,1fr)}
  .pipe-split{grid-template-columns:1fr}
  .pipe-forecast-row{grid-template-columns:1fr}
}
@media(max-width:640px){
  .hero{height:320px}
  .hero-badge{top:16px;right:16px;padding:12px 18px}
  .hero-badge img{width:36px;height:36px}
  .hero-badge-text h1{font-size:1.3rem}
  .hs{padding:14px 10px}.hs-val{font-size:1.4rem}
  .dash-tab{padding:12px 12px 10px;font-size:13px}
  .lb-card{flex-direction:column}
  .lb-metrics{width:100%;min-width:0}
  .lb-wrap{padding:22px 16px 40px}
  .pipeline-section{padding:22px 16px}
  .pipe-kpi-row{grid-template-columns:1fr}
  .card-grid{grid-template-columns:1fr}
  .rich-thumb{flex:0 0 100px;width:100px}
  .content{padding:0 16px 40px}
  .section-banner{flex-direction:column;align-items:flex-start;gap:8px}
  .section-avg{margin-top:4px}
  .modal{border-radius:4px}
  .m-hdr,.m-body,.m-prog,.m-footer{padding-left:16px;padding-right:16px}
  .det-grid{grid-template-columns:1fr}
  .search-wrap{padding:10px 16px}
  .search-input{font-size:.95rem;padding:12px 14px 12px 48px}
}

/* ── Search bar ─────────────────────────────────────────── */
.search-wrap{
  position:sticky;top:40px;z-index:90;
  background:var(--page-warm);
  padding:12px 0 16px;
  border-bottom:1px solid var(--border);
}
.search-input{
  width:100%;box-sizing:border-box;
  padding:12px 14px 12px 44px;
  font-size:.9rem;font-family:inherit;font-weight:400;
  background:var(--white);color:var(--txt);
  border:1px solid var(--border);border-radius:4px;
  outline:none;transition:border-color .15s ease;
}
.search-input::placeholder{color:#bbb}
.search-input:focus{border-color:var(--navy)}
.search-icon{
  position:absolute;left:12px;top:50%;transform:translateY(-50%);
  pointer-events:none;color:var(--txt-secondary);
}
.search-no-match{
  text-align:center;padding:32px 0;color:var(--txt-secondary);display:none;
}

/* ═══ CHAIN DISPLAY ═══════════════════════════════════════ */
.chain-toggle{
  width:100%;background:var(--muted-bg);border:none;border-top:1px solid var(--border);
  padding:10px 14px;color:var(--txt-secondary);font-size:.78rem;font-weight:500;
  cursor:pointer;display:flex;align-items:center;justify-content:space-between;
  transition:var(--t);
}
.chain-toggle:hover{background:var(--white);color:var(--txt)}
.chain-toggle .chain-chev{font-size:10px;color:var(--txt-secondary);transition:transform .15s ease;flex-shrink:0}
.chain-toggle.expanded .chain-chev{transform:rotate(180deg)}
.chain-toggle .chain-lbl{display:flex;align-items:center;gap:6px;color:var(--txt)}
.chain-panel{max-height:0;overflow:hidden;transition:max-height .35s ease}
.chain-panel.expanded{max-height:1200px}
.chain-inner{padding:12px 22px 16px}
.chain-diagram{display:flex;flex-direction:column;align-items:center;gap:0}
.chain-link-box{
  width:100%;background:var(--white);border:2px solid var(--navy);
  border-radius:6px;padding:10px 14px;position:relative;
}
.chain-link-box.chain-anchor{
  border:2px solid var(--navy);background:rgba(27,58,92,.04);
}
.chain-link-addr{font-size:.82rem;font-weight:500;color:var(--txt);letter-spacing:-.01em}
.chain-link-detail{font-size:.72rem;color:var(--txt-secondary);margin-top:2px}
.chain-link-status{
  display:inline-block;font-size:.62rem;font-weight:700;letter-spacing:.5px;
  text-transform:uppercase;padding:2px 8px;border-radius:4px;margin-top:4px;
}
.chain-link-status.chain-st-active{background:rgba(197,217,58,.15);color:var(--olive-text)}
.chain-link-status.chain-st-problem{background:rgba(150,45,62,.12);color:var(--claret)}
.chain-link-status.chain-st-complete{background:rgba(27,58,92,.1);color:var(--navy)}
.chain-link-status.chain-st-default{background:var(--muted-bg);color:var(--txt-secondary)}
.chain-connector{
  width:2px;height:18px;background:var(--navy);margin:0 auto;
}
.chain-pos-label{
  font-size:10px;text-transform:uppercase;letter-spacing:.05em;
  color:var(--txt-secondary);font-weight:500;margin-bottom:6px;text-align:center;
}

/* ═══ NEEDS ATTENTION + COLLAPSIBLE SECTIONS ═══════════ */
.needs-attention-region{
  background:var(--white);border-radius:6px;padding:8px 16px 20px;margin-bottom:24px;
  border:2px solid var(--navy);
}
.section-collapse-hdr{
  width:100%;display:flex;justify-content:space-between;align-items:center;
  text-align:left;background:transparent;border:none;cursor:pointer;
  padding:16px 4px 12px;
}
.section-collapse-hdr h2{
  font-size:20px;font-weight:700;color:#1B3A5C;margin:0;
  display:flex;align-items:center;gap:10px;flex-wrap:wrap;
}
.na-heading-dot{
  width:8px;height:8px;border-radius:50%;background:var(--claret);flex-shrink:0;
}
.na-count-badge,.sec-count-badge{
  font-size:12px;font-weight:600;padding:2px 10px;border-radius:3px;
  background:var(--navy);color:#fff;
}
.section-collapse-hdr .hdr-chev{font-size:10px;color:var(--txt-secondary);flex-shrink:0;transition:transform .15s ease;display:inline-block}
.section-collapse-hdr.collapsed .hdr-chev{transform:rotate(-90deg)}
.section-collapse-body{overflow:hidden}
.section-collapse-body:not(.open){display:none}
.na-empty{padding:24px;text-align:center;color:var(--txt-secondary)}
.card-grid-na{grid-template-columns:repeat(2,1fr)}
.prop-card-na{min-height:auto}
.na-overdue{font-size:14px;font-weight:600;color:var(--claret);margin:0 0 6px}
.na-action{font-size:.85rem;color:var(--txt);line-height:1.4;margin-bottom:10px}
.na-cta{
  display:inline-flex;align-items:center;justify-content:center;
  padding:8px 14px;border-radius:4px;font-size:.8rem;font-weight:500;
  background:var(--navy);color:#fff;text-decoration:none;margin-bottom:12px;
}
.na-cta:hover{filter:brightness(1.05);transition:var(--t)}
.m-pipe-row{display:flex;flex-direction:column;gap:8px;margin-bottom:12px;flex-wrap:nowrap}
.m-pipe-row label{font-size:10px;font-weight:400;color:var(--txt-secondary);text-transform:uppercase;letter-spacing:.04em}
.m-pipe-row select,.m-pipe-row input{
  font-size:.85rem;padding:8px 10px;border:1px solid var(--border);border-radius:4px;background:var(--white);color:var(--txt);
}
.m-pipe-row select:focus,.m-pipe-row input:focus{outline:none;border-color:var(--navy)}
.m-pipe-save{background:var(--navy);color:#fff;border:none;border-radius:4px;padding:8px 14px;font-size:.78rem;font-weight:500;cursor:pointer;margin-top:4px;transition:var(--t)}
.m-pipe-save:hover{filter:brightness(1.05)}
@media(max-width:960px){.card-grid-na{grid-template-columns:1fr}}
</style>
</head>
<body>

{# ═══ PROPERTY CARD MACROS ═══════════════════════════════ #}
{% macro rich_prop_card(p, triggers=none) %}
{% set cl = p.chain_links|default([]) %}
{% set cid = ('na-' ~ p.id) if triggers else p.id %}
<div class="rich-card prop-card{% if triggers %} prop-card-na{% endif %} rich-card--{{ p._rail }}" {% if triggers %}id="card-na-{{ p.id }}" data-prop-id="{{ p.id }}"{% else %}id="card-{{ p.id }}"{% endif %}>
  <div class="rich-thumb" aria-hidden="true">
    {% set thumb_url = (p.image_url or '')|trim %}
    {% if thumb_url %}
    <img src="{{ thumb_url }}" alt="" loading="lazy">
    {% else %}
    <div class="rich-thumb-placeholder">
      <img class="rich-thumb-ph-logo" src="/static/logo.png" width="48" height="48" alt="" loading="lazy">
    </div>
    {% endif %}
  </div>
  <div class="rich-col">
    <div class="rich-body">
      <div class="rich-badge">{{ p._card_badge_text }}</div>
      {% if triggers and triggers|length > 0 %}
      {% set primary = triggers[0] %}
      <div class="rich-na-strip">
        {% if primary.days_overdue > 0 %}<div class="na-overdue">{{ primary.days_overdue }} days overdue</div>{% elif primary.days_overdue == 0 %}<div class="na-overdue">Immediate</div>{% endif %}
        {% if primary.suggested_action %}<p class="rich-na-action">{{ primary.suggested_action }}</p>{% endif %}
        {% if primary.quick_action %}<a class="rich-na-cta" href="{{ primary.quick_action.href }}" {% if primary.quick_action.href == '#' %}onclick="event.stopPropagation();return false;"{% else %}onclick="event.stopPropagation();"{% endif %}>{{ primary.quick_action.label }}</a>{% endif %}
      </div>
      {% endif %}
      <div class="rich-row2">
        <div class="rich-addrblock">
          <div class="rich-addr">{{ p.address }}{% if p.location %}, {{ p.location }}{% endif %}</div>
          {% if p._card_subtitle %}<div class="rich-sub">{{ p._card_subtitle }}</div>{% endif %}
        </div>
        {% if p._pipe_fee %}
        <div class="rich-feecol">
          <div class="rich-fee">&pound;{{ "{:,.0f}".format(p._pipe_fee) }}</div>
          <div class="rich-fee-lbl">Commission</div>
        </div>
        {% endif %}
      </div>
      <div class="rich-prog">
        <div class="rich-prog-track"><div class="rich-prog-fill rich-prog-fill--{{ p._rail }}" style="width:{{ p._milestones_pct }}%"></div></div>
      </div>
      <div class="rich-chips">
        {% for c in p._milestone_chips %}
        <span class="rich-chip rich-chip--{{ c.state }}">{{ c.label }}</span>
        {% endfor %}
      </div>
      <div class="rich-footer">
        <div class="rich-foot-left">
          <div class="rich-meta"><span class="rich-meta-l">Days</span><span class="rich-meta-v">{{ p._bucket_days }}</span></div>
          <div class="rich-meta">
            <span class="rich-meta-l">Target</span>
            {% if p._card_target_missing %}<span class="rich-meta-v rich-meta-v--muted">No target</span>
            {% else %}<span class="rich-meta-v {{ 'rich-meta-v--warn' if p._card_target_warn else 'rich-meta-v--ok' }}">{{ p._card_target_days }} days</span>{% endif %}
          </div>
          <span class="rich-chain-pill">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>
            {% if cl|length > 0 %}Chain ({{ cl|length }}){% else %}No chain{% endif %}
          </span>
        </div>
        {% if p._card_neg_initials %}
        <div class="rich-neg">
          <span class="rich-neg-av rich-neg-av--{{ p._rail }}">{{ p._card_neg_initials }}</span>
          {% if p._card_neg_name %}<span class="rich-neg-nm">{{ p._card_neg_name }}</span>{% endif %}
        </div>
        {% endif %}
      </div>
    </div>
    <button type="button" class="chain-toggle" data-chain-id="{{ cid }}" onclick="event.stopPropagation();toggleChain('{{ cid }}')">
      <span class="chain-lbl">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>
        Full chain {% if cl|length > 0 %}({{ cl|length }} link{{ 's' if cl|length != 1 }}){% else %}(no links){% endif %}
      </span>
      <span class="chain-chev" aria-hidden="true">&#9660;</span>
    </button>
    <div class="chain-panel" id="chainPanel-{{ cid }}">
      {% if cl|length > 0 %}
      <div class="chain-inner">
        <div class="chain-diagram">
          {% set above = cl|selectattr('chain_position','equalto','above')|list %}
          {% set below = cl|selectattr('chain_position','equalto','below')|list %}
          {% if above|length > 0 %}
          <div class="chain-pos-label">Above</div>
          {% for link in above %}
          <div class="chain-link-box">
            <div class="chain-link-addr">{{ link.link_address or 'Unknown' }}</div>
            <div class="chain-link-detail">
              {% if link.estate_agent %}{{ link.estate_agent }}{% endif %}
              {% if link.buyer_solicitor %} &bull; {{ link.buyer_solicitor }}{% endif %}
              {% if link.seller_solicitor %} &bull; {{ link.seller_solicitor }}{% endif %}
            </div>
            {% if link.status %}<span class="chain-link-status chain-st-{{ link.status|lower|replace(' ','-') if link.status|lower in ['active','problem','complete'] else 'default' }}">{{ link.status }}</span>{% endif %}
          </div>
          {% if not loop.last %}<div class="chain-connector"></div>{% endif %}
          {% endfor %}
          <div class="chain-connector"></div>
          {% endif %}
          <div class="chain-link-box chain-anchor">
            <div class="chain-link-addr">{{ p.address }}</div>
            <div class="chain-link-detail" style="color:var(--navy);font-weight:600">Subject Property</div>
          </div>
          {% if below|length > 0 %}
          <div class="chain-connector"></div>
          <div class="chain-pos-label">Below</div>
          {% for link in below %}
          <div class="chain-link-box">
            <div class="chain-link-addr">{{ link.link_address or 'Unknown' }}</div>
            <div class="chain-link-detail">
              {% if link.estate_agent %}{{ link.estate_agent }}{% endif %}
              {% if link.buyer_solicitor %} &bull; {{ link.buyer_solicitor }}{% endif %}
              {% if link.seller_solicitor %} &bull; {{ link.seller_solicitor }}{% endif %}
            </div>
            {% if link.status %}<span class="chain-link-status chain-st-{{ link.status|lower|replace(' ','-') if link.status|lower in ['active','problem','complete'] else 'default' }}">{{ link.status }}</span>{% endif %}
          </div>
          {% if not loop.last %}<div class="chain-connector"></div>{% endif %}
          {% endfor %}
          {% endif %}
        </div>
      </div>
      {% endif %}
    </div>
  </div>
</div>
{% endmacro %}

{% macro prop_card(p) %}{{ rich_prop_card(p) }}{% endmacro %}
{% macro na_card(p, triggers) %}{{ rich_prop_card(p, triggers) }}{% endmacro %}

{% macro dash_leaderboard_panel(lb) %}
<div id="tab-panel-{{ lb.tab_id }}" class="tab-panel">
  <div class="lb-wrap">
    <div class="lb-header">
      <h2>{{ lb.title }}</h2>
      <p>{{ lb.subtitle }}</p>
    </div>
    <p class="lb-metric-note" title="{{ lb.metric_note }}">{{ lb.metric_note }}</p>
    <div class="lb-cards">
      {% for e in lb.rows %}
      <article class="lb-card">
        <div class="lb-rank-col">
          <div class="lb-rank-num">{{ e.rank }}</div>
          {% set mv = e.movement %}
          <div class="lb-move">{% if mv.startswith('▲') %}<span class="lb-arr lb-arr--up">▲</span><span class="lb-arr-rest">{{ mv[1:] }}</span>{% elif mv.startswith('▼') %}<span class="lb-arr lb-arr--down">▼</span><span class="lb-arr-rest">{{ mv[1:] }}</span>{% else %}<span class="lb-arr lb-arr--flat">{{ mv }}</span>{% endif %}</div>
        </div>
        <div class="lb-mid">
          <div class="lb-company">{{ e.company }}</div>
          <div class="lb-location">{{ e.location }}</div>
          <div class="lb-stars">{{ e.rating|round(1) }} &#9733;</div>
          {% if e.rank == 1 %}<span class="lb-badge-rec">Recommended</span>{% endif %}
        </div>
        <div class="lb-metrics">
          <div>
            <div class="lb-metric-lbl">Avg time</div>
            <div><span class="lb-pill {% if e.avg_days < 70 %}lb-pill--good{% elif e.avg_days <= 90 %}lb-pill--mid{% else %}lb-pill--warn{% endif %}">{{ e.avg_days }} day{% if e.avg_days != 1 %}s{% endif %}</span></div>
          </div>
          <div>
            <div class="lb-metric-lbl">Response</div>
            <div class="lb-metric-val">{{ e.response }}</div>
          </div>
          <div>
            <div class="lb-metric-lbl">Completion</div>
            <div class="lb-metric-val">{{ e.comp_pct }}</div>
          </div>
          <div>
            <div class="lb-metric-lbl">Transactions</div>
            <div class="lb-metric-val">{{ e.txns }}</div>
          </div>
        </div>
      </article>
      {% endfor %}
    </div>
  </div>
</div>
{% endmacro %}

<!-- ═══ HERO ══════════════════════════════════════════════ -->
<div class="hero">
  <img class="hero-img" src="/static/street-scene.PNG" alt="NUVU sold boards">
  <div class="hero-badge">
    <div class="hero-badge-top">
      <img src="/static/logo.png" alt="NUVU">
      <h1>NUVU</h1>
    </div>
    <div class="hero-badge-strapline">Progression Not Updates</div>
  </div>
  <div class="hero-stats">
    <div class="hs" id="stat-active"><div class="hs-val">{{ stats.active }}</div><div class="hs-lbl">Active</div></div>
    <div class="hs" id="stat-on-track"><div class="hs-val">{{ stats.on_track }}</div><div class="hs-lbl">On Track</div></div>
    <div class="hs" id="stat-needs-attention"><div class="hs-val{% if stats.needs_attention > 0 %} hs-val--warn{% endif %}">{{ stats.needs_attention }}</div><div class="hs-lbl">Needs Attention</div></div>
    <div class="hs" id="stat-exchanged"><div class="hs-val">{{ stats.exchanged }}</div><div class="hs-lbl">Exchanged</div></div>
    <div class="hs" id="stat-pipeline-value"><div class="hs-val">&pound;{{ "{:,.0f}".format(stats.pipeline_value) }}</div><div class="hs-lbl">Pipeline Value</div></div>
  </div>
</div>

<nav class="dash-tab-toolbar" aria-label="Dashboard views">
  <div class="dash-tab-inner">
    <button type="button" class="dash-tab dash-tab--active" data-tab="properties">Properties</button>
    <button type="button" class="dash-tab" data-tab="pipeline">Pipeline</button>
    <button type="button" class="dash-tab" data-tab="portal">Portal</button>
    <button type="button" class="dash-tab" data-tab="solicitors">Solicitors</button>
    <button type="button" class="dash-tab" data-tab="mortgage">Mortgage</button>
    <button type="button" class="dash-tab" data-tab="surveyors">Surveyors</button>
    <button type="button" class="dash-tab" data-tab="removals">Removals</button>
  </div>
</nav>

<div class="dash-tab-panels">

<div id="tab-panel-properties" class="tab-panel tab-panel--active">

<!-- ═══ SEARCH BAR (sticky) ════════════════════════════════ -->
<div class="search-wrap" id="searchWrap">
  <div style="position:relative;max-width:640px;margin:0 auto">
    <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input class="search-input" id="searchInput" type="text" placeholder="Search by address, buyer or solicitor..." autocomplete="off">
  </div>
</div>

<!-- ═══ MAIN CONTENT — NEEDS ATTENTION + TIME BUCKETS ═════ -->
<div class="content">
<div class="search-no-match" id="searchNoMatch">No properties found</div>
{% set nai = needs_attention_items|default([]) %}

  <div class="needs-attention-region" id="section-needs-attention">
    <button type="button" class="section-collapse-hdr" id="hdr-needs-attention" data-panel="panel-needs-attention">
      <span style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <h2>Needs attention</h2>
        <span class="na-count-badge">{{ nai|length }}</span>
      </span>
      <span class="hdr-chev" aria-hidden="true">&#9660;</span>
    </button>
    <div class="section-collapse-body open" id="panel-needs-attention">
      <div class="card-grid card-grid-na">
        {% for item in nai[:3] %}
        {{ na_card(item.property, item.triggers) }}
        {% endfor %}
      </div>
      {% if nai|length > 3 %}
      <button class="show-more-btn" id="showMore-needs-attention">
        Show More ({{ nai|length - 3 }})
        <span class="sm-chev" aria-hidden="true">&#9660;</span>
      </button>
      <div class="show-more-panel" id="morePanel-needs-attention">
        <div class="card-grid card-grid-na">
          {% for item in nai[3:] %}
          {{ na_card(item.property, item.triggers) }}
          {% endfor %}
        </div>
      </div>
      {% endif %}
      {% if nai|length == 0 %}
      <p class="na-empty">No properties need attention right now.</p>
      {% endif %}
    </div>
  </div>

  {% for sec in sections %}
  <div class="dash-section" id="section-{{ sec.id }}">
    <button type="button" class="section-collapse-hdr" data-panel="panel-{{ sec.id }}">
      <span style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <h2>{{ sec.title }}</h2>
        <span class="sec-count-badge">{{ sec.count }}</span>
      </span>
      <span class="hdr-chev" aria-hidden="true">&#9660;</span>
    </button>
    <div class="section-collapse-body open" id="panel-{{ sec.id }}">
      <div class="section-banner {{ sec.border_class }}" style="border-left:none;padding-left:0;margin-left:0">
        <div class="section-banner-left">
          <p style="margin:0">{{ sec.subtitle }} &mdash; {{ sec.count }} propert{% if sec.count == 1 %}y{% else %}ies{% endif %}</p>
        </div>
        <div class="section-banner-right">
          <div class="section-avg">
            <div class="avg-label">Avg Completion</div>
            <div class="avg-bar-wrap">
              <div class="avg-bar"><div class="avg-bar-fill" style="width:{{ sec.avg_progress }}%;background:{{ sec.avg_color }}"></div></div>
              <span class="avg-pct">{{ sec.avg_progress }}%</span>
            </div>
          </div>
        </div>
      </div>
      <div class="card-grid">
        {% for p in sec.visible %}
        {{ prop_card(p) }}
        {% endfor %}
      </div>
      {% set total_extra = sec.hidden|length + sec.extra_count %}
      {% if total_extra > 0 %}
      <button class="show-more-btn" id="showMore-{{ sec.id }}">
        Show More ({{ total_extra }})
        <span class="sm-chev" aria-hidden="true">&#9660;</span>
      </button>
      <div class="show-more-panel" id="morePanel-{{ sec.id }}">
        {% if sec.hidden %}
        <div class="card-grid">
          {% for p in sec.hidden %}
          {{ prop_card(p) }}
          {% endfor %}
        </div>
        {% endif %}
        {% if sec.extra_count > 0 %}
        <div class="extra-summary">
          <span>+ {{ sec.extra_count }} more properties</span>
          <span class="extra-note">Connect to your CRM for full pipeline view</span>
        </div>
        {% endif %}
      </div>
      {% endif %}
    </div>
  </div>
  {% endfor %}

</div>

</div>

<!-- ═══ PIPELINE FORECAST (read-only; Pipeline tab only) ═ -->
<div id="tab-panel-pipeline" class="tab-panel">
<div class="pipeline-section" id="pipelineSection">
  <div class="pipe-inner">
    <div class="pipeline-header">
      <div>
        <div class="pipeline-title">Pipeline forecast</div>
        <div class="pipeline-sub">{{ pipeline.subtitle }}</div>
      </div>
      <div class="ahead-badge{% if pipeline.badge_caution %} caution{% endif %}">{{ pipeline.badge_text }}</div>
    </div>
    <div class="pipe-kpi-row">
      {% for k in pipeline.kpi_cards %}
      <div class="pipe-kpi">
        <div class="pipe-kpi-lbl">{{ k.label }}</div>
        <div class="pipe-kpi-val">{{ k.value }}</div>
        {% if k.sub %}<div class="pipe-kpi-sub">{{ k.sub }}</div>{% endif %}
      </div>
      {% endfor %}
    </div>
    <div class="pipe-split">
      <div class="pipe-panel">
        <div class="pipe-panel-h">Fee income forecast</div>
        <div class="pipe-panel-sub">{{ pipeline.fee_chart_subtitle }}</div>
        <div class="pipe-fee-chart">
          {% for b in pipeline.fee_bars %}
          <div class="pipe-fee-col">
            <div class="pipe-fee-bar-wrap">
              <div class="pipe-fee-bar{% if b.remainder %} pipe-fee-bar--remainder{% endif %}" style="height:{{ b.h_pct }}%"><span>&pound;{{ "{:,.0f}".format(b.fee) }}</span></div>
            </div>
            <div class="pipe-fee-x">{{ b.label }}</div>
          </div>
          {% endfor %}
        </div>
        {% if pipeline.show_fee_chart_hint %}
        <p class="pipe-hint">Milestone data will populate this chart as progression updates are recorded.</p>
        {% endif %}
      </div>
      <div class="pipe-panel">
        <div class="pipe-panel-h">Sales progression funnel</div>
        <div class="pipe-panel-sub">Active cases only &mdash; share reaching each milestone (cumulative)</div>
        <div class="pipe-funnel-rows">
          {% for f in pipeline.funnel %}
          <div class="pipe-fun-row">
            <div class="pipe-fun-lbl">{{ f.label }}</div>
            <div class="pipe-fun-track"><div class="pipe-fun-fill" style="width:{{ f.pct }}%;background:{{ f.fill }}"></div></div>
            <div class="pipe-fun-pct">{{ f.pct }}%</div>
          </div>
          {% endfor %}
        </div>
        {% if pipeline.show_funnel_hint %}
        <p class="pipe-hint">Update milestones on each property to see progression here.</p>
        {% endif %}
      </div>
    </div>
    <div class="pipe-forecast-row">
      <div class="pipe-fc pipe-fc-m1">
        <div class="pipe-fc-h">{{ pipeline.month_cards[0].title }}</div>
        <div class="pipe-fc-count">{{ pipeline.month_cards[0].count }} cases</div>
        <div class="pipe-fc-val">&pound;{{ "{:,.0f}".format(pipeline.month_cards[0].fee) }} pipeline fee</div>
        <div class="pipe-fc-note">{{ pipeline.month_cards[0].note }}</div>
      </div>
      <div class="pipe-fc pipe-fc-navy">
        <div class="pipe-fc-h">{{ pipeline.month_cards[1].title }}</div>
        <div class="pipe-fc-count">{{ pipeline.month_cards[1].count }} cases</div>
        <div class="pipe-fc-val">&pound;{{ "{:,.0f}".format(pipeline.month_cards[1].fee) }} pipeline fee</div>
        <div class="pipe-fc-note">{{ pipeline.month_cards[1].note }}</div>
      </div>
      <div class="pipe-fc pipe-fc-amber">
        <div class="pipe-fc-h">{{ pipeline.month_cards[2].title }}</div>
        <div class="pipe-fc-count">{{ pipeline.month_cards[2].count }} cases</div>
        <div class="pipe-fc-val">&pound;{{ "{:,.0f}".format(pipeline.month_cards[2].fee) }} pipeline fee</div>
        <div class="pipe-fc-note">{{ pipeline.month_cards[2].note }}</div>
      </div>
    </div>
  </div>
</div>
</div>

<div id="tab-panel-portal" class="tab-panel">
  <div class="portal-dash-card">
    <h2>Customer Portal</h2>
    <p>Manage seller portal links, track form completion, and view submitted responses. Full portal admin for staff is planned; today, portal journeys live under <code>/portal</code> (buyer/vendor demo login) and TA6/TA10 flows under <code>/portal/form</code>.</p>
    <p class="portal-dash-card__muted">There is no separate consolidated portal admin dashboard page in this codebase yet. Per-property portal status, seller links, and staff read-only previews are available from each property card modal (Buyer &amp; vendor portal and TA6 / TA10 sections).</p>
    <p><a class="na-cta" href="/portal" target="_blank" rel="noopener">Open portal entry</a></p>
  </div>
</div>

{% for lb in leaderboard_tabs %}
{{ dash_leaderboard_panel(lb) }}
{% endfor %}

</div>

<!-- ═══ PROPERTY MODAL ══════════════════════════════════ -->
<div class="modal-overlay" id="modalOverlay">
  <div class="modal" id="modalBox">
    <div class="m-hdr">
      <div>
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px">
          <h2 id="mAddr"></h2>
          <span id="mStatusChip" class="pc-badge" style="display:none"></span>
        </div>
        <div class="m-loc" id="mLoc"></div>
      </div>
      <div style="display:flex;align-items:flex-start;gap:8px">
        <div class="m-price" id="mPrice"></div>
        <button type="button" class="m-close" id="mCloseBtn" aria-label="Close">&times;</button>
      </div>
    </div>

    <div class="m-prog">
      <div class="m-prog-bar"><div class="m-prog-fill" id="mProgFill"></div></div>
      <div class="m-prog-labels"><span>Offer Accepted</span><span id="mProgPct"></span><span>Completion</span></div>
    </div>

    <div class="m-body">
      <hr class="m-div">
      <div id="mAlertBox" class="m-alert" style="display:none">
        <span id="mAlertTxt"></span>
      </div>
      <div class="m-next">
        <div class="m-next-lbl">Next Action</div>
        <div class="m-next-txt" id="mNextAction"></div>
      </div>
      <div class="m-actions">
        <button type="button" class="m-btn m-btn-call" id="mBtnCall">
          <span id="mCallLbl">Call Buyer</span>
        </button>
        <button type="button" class="m-btn m-btn-done" id="mBtnDone">Mark Done</button>
        <button type="button" class="m-btn m-btn-outline" id="mBtnEmail">Email</button>
      </div>
      <div class="m-pipe-row" id="mPipeRow" style="display:none">
        <label for="mChainStatus">Chain status</label>
        <select id="mChainStatus">
          <option value="stable">Stable</option>
          <option value="at_risk">At risk</option>
          <option value="broken">Broken</option>
        </select>
        <label for="mLocalAuthority">Local authority (search turnaround)</label>
        <input type="text" id="mLocalAuthority" placeholder="e.g. Westmorland and Furness" autocomplete="off">
        <button type="button" class="m-pipe-save" id="mPipeSave">Save pipeline fields</button>
      </div>
      <hr class="m-div">
      <div class="m-ms">
        <h3>Milestones</h3>
        <div class="ms-list" id="mMsList"></div>
      </div>
      <hr class="m-div">
      <div class="m-portal-forms" id="mPortalForms"></div>
      <hr class="m-div">
      <div class="m-ms">
        <h3>Notes &amp; Activity</h3>
        <div id="mActivityList"></div>
      </div>
      <hr class="m-div">
      <button type="button" class="m-det-toggle" id="mDetToggle">
        Full Details
        <span class="det-chev" aria-hidden="true">&#9660;</span>
      </button>
      <div class="m-det-panel" id="mDetPanel">
        <div class="m-det-inner">
          <div class="det-grid" id="mDetGrid"></div>
          <div class="d-full" id="mChain"></div>
        </div>
      </div>
    </div>
    <div class="m-footer"></div>
  </div>
</div>

<!-- ═══ JAVASCRIPT — all getElementById, zero inline onclick ═ -->
<script>
(function(){
  "use strict";

  var PROPS = {{ properties_json|safe }};
  var currentProp = null;

  /* ── DOM refs ─────────────────────────────────────── */
  var overlay   = document.getElementById("modalOverlay");
  var modalBox  = document.getElementById("modalBox");
  var closeBtn  = document.getElementById("mCloseBtn");
  var mAddr     = document.getElementById("mAddr");
  var mLoc      = document.getElementById("mLoc");
  var mPrice    = document.getElementById("mPrice");
  var mProgFill = document.getElementById("mProgFill");
  var mProgPct  = document.getElementById("mProgPct");
  var mAlertBox = document.getElementById("mAlertBox");
  var mAlertTxt = document.getElementById("mAlertTxt");
  var mNextAction = document.getElementById("mNextAction");
  var mCallLbl  = document.getElementById("mCallLbl");
  var mBtnCall  = document.getElementById("mBtnCall");
  var mBtnDone  = document.getElementById("mBtnDone");
  var mBtnEmail = document.getElementById("mBtnEmail");
  var mMsList   = document.getElementById("mMsList");
  var mPortalForms = document.getElementById("mPortalForms");
  var mDetToggle = document.getElementById("mDetToggle");
  var mDetPanel  = document.getElementById("mDetPanel");
  var mDetGrid   = document.getElementById("mDetGrid");
  var mChain     = document.getElementById("mChain");
  var mPipeRow   = document.getElementById("mPipeRow");
  var mChainStatus = document.getElementById("mChainStatus");
  var mLocalAuthority = document.getElementById("mLocalAuthority");
  var mPipeSave  = document.getElementById("mPipeSave");
  var mStatusChip = document.getElementById("mStatusChip");

  function fmt(d){
    if(!d) return "\u2014";
    var dt=new Date(d);
    return dt.toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric"});
  }
  function patchProgression(progId,field,value,onSuccess){
    var body={};body[field]=value;
    fetch("/api/progression/"+encodeURIComponent(progId),{
      method:"PATCH",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(body)
    }).then(function(r){
      return r.text().then(function(t){
        var j=null;try{j=JSON.parse(t);}catch(e){}
        return {r:r,j:j,t:t};
      });
    }).then(function(x){
      if(!x.r.ok){
        alert("Save failed: HTTP "+x.r.status+(x.j&&x.j.error?" — "+x.j.error:""));
        return;
      }
      if(x.j&&x.j.ok){if(onSuccess)onSuccess();}
      else{alert("Save failed: "+((x.j&&x.j.error)||x.t||"Unknown error"));}
    }).catch(function(e){alert("Network error: "+e.message);});
  }

  function mirrorMilestoneFieldOnProp(field,val){
    var v=val?val:null;
    if(field==="offer_accepted")currentProp.offer_date=v;
    else if(field==="memo_sent")currentProp.memo_sent=v;
    else if(field==="searches_ordered")currentProp.searches_ordered=v;
    else if(field==="searches_received")currentProp.searches_received=v;
    else if(field==="survey_instructed")currentProp.survey_instructed=v;
    else if(field==="mortgage_offered")currentProp.mortgage_offered=v;
    else if(field==="draft_contract_sent")currentProp.draft_contract_sent=v;
    else if(field==="enquiries_raised")currentProp.enquiries_raised=v;
    else if(field==="enquiries_answered")currentProp.enquiries_answered=v;
    else if(field==="exchange_date")currentProp.exchange_target=v;
    else if(field==="completion_date")currentProp.completion_target=v;
    else if(field==="protocol_forms_returned")currentProp.protocol_forms_returned=v;
    else if(field==="seller_forms_returned")currentProp.seller_forms_returned=v;
  }

  function price(n){ return "\u00a3"+n.toLocaleString(); }
  function fillCls(s){
    if(s==="stalled")return "clr-stalled";
    if(s==="at-risk")return "clr-at-risk";
    if(s==="exchanged")return "clr-exchanged";
    return "clr-on-track";
  }
  function alertCls(s){
    if(s==="stalled")return "m-alert-red";
    if(s==="at-risk")return "m-alert-amber";
    if(s==="exchanged")return "m-alert-green";
    return "m-alert-green";
  }

  /* ── open modal ───────────────────────────────────── */
  function openModal(id){
    var p=null;
    for(var i=0;i<PROPS.length;i++){if(String(PROPS[i].id)===String(id)){p=PROPS[i];break;}}
    if(!p)return;
    currentProp=p;

    mAddr.textContent=p.address;
    mLoc.textContent=p.location;
    mPrice.textContent=price(p.price);
    if(mStatusChip){
      var sl=(p.status_label||"").toString().toUpperCase();
      if(sl){
        mStatusChip.style.display="inline-block";
        mStatusChip.textContent=sl;
        mStatusChip.className="pc-badge pc-badge--"+(p.status||"on-track");
      }else{
        mStatusChip.style.display="none";
        mStatusChip.textContent="";
      }
    }

    mProgFill.style.width=p.progress+"%";
    mProgFill.className="m-prog-fill "+fillCls(p.status);
    mProgPct.textContent=p.progress+"% complete";

    if(p.alert){
      mAlertBox.style.display="flex";
      mAlertBox.className="m-alert "+alertCls(p.status);
      mAlertTxt.textContent=p.alert;
    }else{
      mAlertBox.style.display="none";
    }

    mNextAction.textContent=p.next_action;
    mCallLbl.textContent="Call "+p.buyer.split(" ").pop();

    if(mPipeRow&&mChainStatus&&mLocalAuthority&&mPipeSave){
      if(p._sales_pipeline_id){
        mPipeRow.style.display="flex";
        mChainStatus.value=p.chain_status||"stable";
        mLocalAuthority.value=p.local_authority||"";
        mPipeSave.setAttribute("data-pipe-id",p._sales_pipeline_id);
      }else{
        mPipeRow.style.display="none";
        mPipeSave.removeAttribute("data-pipe-id");
      }
    }

    var h="";
    for(var m=0;m<p.milestones.length;m++){
      var ms=p.milestones[m];
      var ic,tx,lc;
      if(ms.done===true){ic="ms-ic done";tx="\u2713";lc="ms-lb done-lb";}
      else if(ms.done===null){ic="ms-ic na";tx="N/A";lc="ms-lb";}
      else{ic="ms-ic pending";tx="";lc="ms-lb ms-pending-lb";}
      var dateStr=ms.date?' <span class="ms-date">'+fmt(ms.date)+'</span>':"";
      var editBtn="";
      if(p._progression_id&&ms.field!=="protocol_forms_returned"){
        editBtn='<button class="ms-edit-btn" data-field="'+ms.field+'" data-idx="'+m+'">Edit</button>';
      }
      h+='<div class="ms-item" id="ms-row-'+m+'"><span class="'+ic+'">'+tx+'</span><span class="'+lc+'">'+ms.label+'</span>'+dateStr+editBtn+'</div>';
    }
    mMsList.innerHTML=h;

    function buildPortalBlock(label,formKey,info){
      info=info||{};
      var sid=info.session_id||"";
      var hasSession=!!sid;
      var html='<div class="portal-form-block">';
      if(hasSession){
        html+='<div class="portal-line"><strong>'+label+'</strong> '+(info.status_line||"In progress")+'</div>'+
          '<div class="portal-actions-row">'+
            '<a class="portal-action-link" href="/portal/form?session_id='+encodeURIComponent(sid)+'&form='+encodeURIComponent(formKey)+'" target="_blank" rel="noopener" title="Read-only seller view of the TA6/TA10 form">View as Seller</a>'+
            '<a class="portal-action-link" href="/portal/review/'+encodeURIComponent(sid)+'" target="_blank" rel="noopener" title="All answers, AI history and completion status">Review Answers</a>'+
          '</div>';
      }else{
        html+='<div class="portal-line empty"><strong>'+label+'</strong> No portal session yet</div>'+
          '<div class="portal-actions-row">'+
            '<button type="button" class="portal-send-btn" disabled title="Coming soon">Send '+label+' Link</button>'+
          '</div>';
      }
      html+='</div>';
      return html;
    }
    var portalProgId=p._portal_progression_id||"";
    var clientPortalH="";
    if(portalProgId){
      clientPortalH='<h3>Buyer &amp; vendor portal</h3>'+
        '<div class="portal-line">Client-facing progression overview for this sale (matches the signed-in portal home).</div>'+
        '<div class="portal-actions-row">'+
        '<a class="portal-action-link" href="/portal/staff/property-home?progression_id='+encodeURIComponent(portalProgId)+'&role=buyer" target="_blank" rel="noopener" title="Staff read-only: buyer portal view for this property">View as Buyer</a>'+
        '<a class="portal-action-link" href="/portal/staff/property-home?progression_id='+encodeURIComponent(portalProgId)+'&role=seller" target="_blank" rel="noopener" title="Staff read-only: seller portal view for this property">View as Seller</a>'+
        '</div>';
    }else{
      clientPortalH='<h3>Buyer &amp; vendor portal</h3>'+
        '<div class="portal-line empty">No Supabase progression linked for this address yet — client portal preview needs a sales_progression row.</div>';
    }
    var p6=p.portal_ta6||{};
    var p10=p.portal_ta10||{};
    var taBlockH='<h3>TA6 / TA10 (seller portal)</h3>'+
      buildPortalBlock("TA6","ta6",p6)+
      buildPortalBlock("TA10","ta10",p10);
    mPortalForms.innerHTML=clientPortalH+'<hr class="m-div" style="margin:14px 0 10px">'+
      taBlockH;

    /* milestone edit button handlers */
    var editBtns=mMsList.querySelectorAll(".ms-edit-btn");
    for(var eb=0;eb<editBtns.length;eb++){
      (function(btn){
        btn.onclick=function(e){
          e.stopPropagation();
          var field=btn.getAttribute("data-field");
          var idx=btn.getAttribute("data-idx");
          var row=document.getElementById("ms-row-"+idx);
          var ms=currentProp.milestones[idx];
          var curVal=ms.date||"";
          row.innerHTML='<span class="ms-ic pending"></span><span class="ms-lb">'+ms.label+'</span>'+
            '<div class="ms-edit-form"><input type="date" id="ms-date-'+idx+'" value="'+curVal+'">'+
            '<button class="ms-save-btn" id="ms-sv-'+idx+'">Save</button>'+
            '<button class="ms-cancel-btn" id="ms-cn-'+idx+'">Cancel</button></div>';
          document.getElementById("ms-sv-"+idx).onclick=function(ev){
            ev.stopPropagation();
            var val=document.getElementById("ms-date-"+idx).value;
            patchProgression(currentProp._progression_id,field,val,function(){
              ms.date=val||"";
              ms.done=!!val;
              mirrorMilestoneFieldOnProp(field,val);
              openModal(currentProp.id);
            });
          };
          document.getElementById("ms-cn-"+idx).onclick=function(ev){
            ev.stopPropagation();
            openModal(currentProp.id);
          };
        };
      })(editBtns[eb]);
    }

    /* notes section */
    var noteFields=[
      {key:"notes",label:"General Notes"},
      {key:"nuvu_notes",label:"NUVU Notes"},
      {key:"buyer_solicitor_notes",label:"Buyer Solicitor Notes"},
      {key:"seller_solicitor_notes",label:"Seller Solicitor Notes"}
    ];
    var ah="";
    for(var nf=0;nf<noteFields.length;nf++){
      var n=noteFields[nf];
      var val=p[n.key]||"";
      var editBtn2=p._progression_id?'<button class="note-edit-btn" data-nkey="'+n.key+'" data-nidx="'+nf+'">Edit</button>':"";
      ah+='<div class="note-block" id="note-blk-'+nf+'">'+
        '<div class="note-block-hdr"><span class="note-block-lbl">'+n.label+'</span>'+editBtn2+'</div>'+
        '<div class="note-block-txt'+(val?'':' empty')+'" id="note-txt-'+nf+'">'+(val||'No notes yet')+'</div></div>';
    }
    if(p.activity&&p.activity.length){
      for(var a=0;a<p.activity.length;a++){
        ah+='<div class="act-item"><div class="act-idx">'+p.activity[a].date+'</div>'+p.activity[a].text+'</div>';
      }
    }
    document.getElementById("mActivityList").innerHTML=ah;

    /* note edit handlers */
    var noteBtns=document.querySelectorAll(".note-edit-btn");
    for(var nb=0;nb<noteBtns.length;nb++){
      (function(btn){
        btn.onclick=function(e){
          e.stopPropagation();
          var nkey=btn.getAttribute("data-nkey");
          var nidx=btn.getAttribute("data-nidx");
          var blk=document.getElementById("note-blk-"+nidx);
          var curVal=currentProp[nkey]||"";
          var nfObj=noteFields[nidx];
          blk.innerHTML='<div class="note-block-hdr"><span class="note-block-lbl">'+nfObj.label+'</span></div>'+
            '<textarea class="note-textarea" id="note-ta-'+nidx+'">'+curVal+'</textarea>'+
            '<div class="note-actions"><button class="note-save-btn" id="note-sv-'+nidx+'">Save</button>'+
            '<button class="note-cancel-btn" id="note-cn-'+nidx+'">Cancel</button></div>';
          document.getElementById("note-sv-"+nidx).onclick=function(ev){
            ev.stopPropagation();
            var val=document.getElementById("note-ta-"+nidx).value;
            patchProgression(currentProp._progression_id,nkey,val,function(){
              currentProp[nkey]=val;
              openModal(currentProp.id);
            });
          };
          document.getElementById("note-cn-"+nidx).onclick=function(ev){
            ev.stopPropagation();
            openModal(currentProp.id);
          };
        };
      })(noteBtns[nb]);
    }

    var rows=[
      ["Buyer",p.buyer],["Buyer Phone",p.buyer_phone],
      ["Buyer Solicitor",p.buyer_solicitor],["Buyer Sol. Phone",p.buyer_sol_phone],
      ["Seller Solicitor",p.seller_solicitor],["Seller Sol. Phone",p.seller_sol_phone],
      ["Offer Accepted",fmt(p.offer_date)],["Memo Sent",fmt(p.memo_sent)],
      ["Searches Ordered",fmt(p.searches_ordered)],["Searches Received",fmt(p.searches_received)],
      ["Enquiries Raised",fmt(p.enquiries_raised)],["Enquiries Answered",fmt(p.enquiries_answered)],
      ["Mortgage Offered",fmt(p.mortgage_offered)],["Survey Instructed",fmt(p.survey_instructed)],
      ["Draft Contract Sent",fmt(p.draft_contract_sent)],["Exchange Target",fmt(p.exchange_target)],
      ["Completion Target",fmt(p.completion_target)],["Duration",p.duration_days+" of "+p.target_days+" days"]
    ];
    var dh="";
    for(var r=0;r<rows.length;r++){
      dh+='<div class="d-r"><span class="d-l">'+rows[r][0]+'</span><span class="d-v">'+rows[r][1]+'</span></div>';
    }
    mDetGrid.innerHTML=dh;
    mChain.innerHTML='<div class="d-full-l">Chain Information</div><div class="d-full-v">'+p.chain+'</div>';

    mDetPanel.classList.remove("expanded");
    mDetToggle.classList.remove("expanded");

    overlay.classList.add("open");
    document.body.style.overflow="hidden";
  }

  function closeModal(){
    overlay.classList.remove("open");
    document.body.style.overflow="";
    currentProp=null;
  }

  /* ── PROPERTY MODAL — event handlers ──────────────── */
  closeBtn.onclick=function(e){e.stopPropagation();closeModal();};
  overlay.onclick=function(e){if(e.target===overlay)closeModal();};
  modalBox.onclick=function(e){e.stopPropagation();};
  document.onkeydown=function(e){
    if(e.key==="Escape"){closeModal();}
  };
  mDetToggle.onclick=function(){mDetPanel.classList.toggle("expanded");mDetToggle.classList.toggle("expanded");};
  mBtnCall.onclick=function(){
    if(!currentProp)return;
    var ph=(currentProp.buyer_phone||"").replace(/\s/g,"");
    if(ph&&ph.length>6)window.location.href="tel:"+ph.replace(/[^\d+]/g,"");
    else alert("Calling "+currentProp.buyer+" on "+currentProp.buyer_phone);
  };
  mBtnDone.onclick=function(){if(currentProp)alert("Marked done for "+currentProp.address+".\n\nAction: "+currentProp.next_action);};
  mBtnEmail.onclick=function(){
    if(!currentProp)return;
    window.location.href="mailto:?subject="+encodeURIComponent(currentProp.address+" — progression");
  };
  if(mPipeSave){
    mPipeSave.onclick=function(ev){
      ev.stopPropagation();
      var pid=mPipeSave.getAttribute("data-pipe-id");
      if(!pid||!currentProp)return;
      fetch("/api/sales-pipeline/"+encodeURIComponent(pid),{
        method:"PATCH",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          chain_status:mChainStatus.value,
          local_authority:mLocalAuthority.value
        })
      }).then(function(r){return r.json().then(function(j){return {r:r,j:j};});})
      .then(function(x){
        if(!x.r.ok){alert((x.j&&x.j.error)||"Save failed");return;}
        currentProp.chain_status=mChainStatus.value;
        currentProp.local_authority=mLocalAuthority.value;
        alert("Saved.");
      }).catch(function(e){alert(e.message);});
    };
  }

  /* ── CARD CLICK HANDLERS ──────────────────────────── */
  for(var i=0;i<PROPS.length;i++){
    (function(pid){
      function go(){openModal(pid);}
      var c1=document.getElementById("card-"+pid);
      var c2=document.getElementById("card-na-"+pid);
      if(c1)c1.onclick=go;
      if(c2)c2.onclick=go;
    })(PROPS[i].id);
  }

  /* ── SECTION COLLAPSE HEADERS ─────────────────────── */
  document.querySelectorAll(".section-collapse-hdr").forEach(function(h){
    h.addEventListener("click",function(){
      var pid=h.getAttribute("data-panel");
      if(!pid)return;
      var panel=document.getElementById(pid);
      if(!panel)return;
      var isOpen=panel.classList.toggle("open");
      h.classList.toggle("collapsed",!isOpen);
    });
  });

  /* ── SHOW MORE TOGGLE HANDLERS ────────────────────── */
  var sectionIds=["needs-attention","bucket-0-30","bucket-31-90","bucket-90-plus"];
  for(var s=0;s<sectionIds.length;s++){
    (function(sid){
      var btn=document.getElementById("showMore-"+sid);
      var panel=document.getElementById("morePanel-"+sid);
      if(btn&&panel){
        btn.onclick=function(){
          var isOpen=panel.classList.contains("open");
          if(isOpen){panel.classList.remove("open");btn.classList.remove("expanded");}
          else{panel.classList.add("open");btn.classList.add("expanded");}
        };
      }
    })(sectionIds[s]);
  }

  /* ── STATS BAR — scroll to sections ───────────────── */
  var statMap={
    "stat-active":"section-bucket-0-30",
    "stat-on-track":"section-bucket-0-30",
    "stat-needs-attention":"section-needs-attention",
    "stat-exchanged":"section-needs-attention",
    "stat-pipeline-value":"section-bucket-0-30"
  };
  var statKeys=Object.keys(statMap);
  for(var k=0;k<statKeys.length;k++){
    (function(statId,targetId){
      var el=document.getElementById(statId);
      if(el){
        el.onclick=function(){
          var target=document.getElementById(targetId);
          if(target)target.scrollIntoView({behavior:"smooth",block:"start"});
        };
      }
    })(statKeys[k],statMap[statKeys[k]]);
  }

  /* ── SEARCH — client-side filter ──────────────────────── */
  var searchInput=document.getElementById("searchInput");
  var searchNoMatch=document.getElementById("searchNoMatch");
  var allCards=document.querySelectorAll(".prop-card");
  var allSections=document.querySelectorAll(".content > .dash-section, .content > .needs-attention-region");
  var allShowMoreBtns=document.querySelectorAll(".show-more-btn");
  var allShowMorePanels=document.querySelectorAll(".show-more-panel");

  function doSearch(){
    var q=searchInput.value.trim().toLowerCase();
    if(q.length>0&&q.length<2){return;}

    if(q.length<2){
      /* restore full view */
      for(var i=0;i<allCards.length;i++) allCards[i].style.display="";
      for(var i=0;i<allSections.length;i++) allSections[i].style.display="";
      for(var i=0;i<allShowMoreBtns.length;i++){allShowMoreBtns[i].style.display="";allShowMoreBtns[i].classList.remove("expanded");}
      for(var i=0;i<allShowMorePanels.length;i++){allShowMorePanels[i].style.display="";allShowMorePanels[i].classList.remove("open");}
      searchNoMatch.style.display="none";
      return;
    }

    var matchIds={};
    for(var i=0;i<PROPS.length;i++){
      var p=PROPS[i];
      var hay=(p.address||"")+" "+(p.buyer||"")+" "+(p.buyer_solicitor||"");
      if(hay.toLowerCase().indexOf(q)!==-1) matchIds[p.id]=true;
    }

    var anyVisible=false;
    for(var i=0;i<allCards.length;i++){
      var cid=allCards[i].id.replace("card-","");
      if(matchIds[cid]){allCards[i].style.display="";anyVisible=true;}
      else{allCards[i].style.display="none";}
    }

    /* hide section banners that have zero visible cards */
    for(var i=0;i<allSections.length;i++){
      var cards=allSections[i].querySelectorAll(".prop-card");
      var hasVisible=false;
      for(var j=0;j<cards.length;j++){
        if(cards[j].style.display!=="none"){hasVisible=true;break;}
      }
      allSections[i].style.display=hasVisible?"":"none";
    }

    /* hide show-more buttons and expand panels so all matches are visible */
    for(var i=0;i<allShowMoreBtns.length;i++) allShowMoreBtns[i].style.display="none";
    for(var i=0;i<allShowMorePanels.length;i++){allShowMorePanels[i].style.display="";allShowMorePanels[i].classList.add("open");}

    searchNoMatch.style.display=anyVisible?"none":"block";
  }

  searchInput.addEventListener("input",doSearch);

  /* ── CHAIN TOGGLE ─────────────────────────────────────── */
  window.toggleChain=function(id){
    var panel=document.getElementById("chainPanel-"+id);
    var btn=document.querySelector('[data-chain-id="'+id+'"]');
    if(panel&&btn){
      panel.classList.toggle("expanded");
      btn.classList.toggle("expanded");
    }
  };

  /* ── Tabbed dashboard (URL hash) ─────────────────────── */
  var DASH_TABS = [
    "properties","pipeline","portal","solicitors","mortgage","surveyors","removals"
  ];
  function syncDashTab(){
    var raw = (location.hash || "").replace(/^#/,"").toLowerCase() || "properties";
    if (DASH_TABS.indexOf(raw) < 0) raw = "properties";
    for (var ti = 0; ti < DASH_TABS.length; ti++) {
      var id = DASH_TABS[ti];
      var panel = document.getElementById("tab-panel-" + id);
      var btn = document.querySelector('.dash-tab[data-tab="' + id + '"]');
      if (panel) {
        if (id === raw) panel.classList.add("tab-panel--active");
        else panel.classList.remove("tab-panel--active");
      }
      if (btn) {
        if (id === raw) btn.classList.add("dash-tab--active");
        else btn.classList.remove("dash-tab--active");
      }
    }
  }
  document.querySelectorAll(".dash-tab").forEach(function(b){
    b.addEventListener("click", function(ev){
      ev.preventDefault();
      var id = b.getAttribute("data-tab");
      if (!id) return;
      if (location.hash === "#" + id) syncDashTab();
      else location.hash = "#" + id;
    });
  });
  window.addEventListener("hashchange", syncDashTab);
  syncDashTab();

})();
</script>
</body>
</html>"""


# Demo leaderboard rows (read-only; future: dedicated leaderboard/reviews table).
LEADERBOARD_TABS = [
    {
        "tab_id": "solicitors",
        "title": "Solicitor Leaderboard",
        "subtitle": "Ranked by average transaction time",
        "metric_note": (
            "Average days reflects each firm's typical contribution to overall "
            "transaction time on the properties we track (demo data)."
        ),
        "rows": [
            {
                "rank": 1,
                "company": "Napthens",
                "location": "Preston, Lancashire",
                "avg_days": 58,
                "response": "3 hrs",
                "comp_pct": "96%",
                "rating": 4.8,
                "txns": 214,
                "movement": "▲ 1",
            },
            {
                "rank": 2,
                "company": "Forbes Solicitors",
                "location": "Blackburn, Lancashire",
                "avg_days": 64,
                "response": "5 hrs",
                "comp_pct": "93%",
                "rating": 4.6,
                "txns": 187,
                "movement": "▼ 1",
            },
            {
                "rank": 3,
                "company": "Harrison Drury",
                "location": "Lancaster, Preston",
                "avg_days": 67,
                "response": "4 hrs",
                "comp_pct": "95%",
                "rating": 4.7,
                "txns": 156,
                "movement": "—",
            },
            {
                "rank": 4,
                "company": "Oglethorpe Sturton",
                "location": "Lancaster",
                "avg_days": 72,
                "response": "6 hrs",
                "comp_pct": "91%",
                "rating": 4.4,
                "txns": 98,
                "movement": "▲ 2",
            },
            {
                "rank": 5,
                "company": "SDA Law",
                "location": "Garstang, Wyre",
                "avg_days": 78,
                "response": "8 hrs",
                "comp_pct": "89%",
                "rating": 4.2,
                "txns": 73,
                "movement": "▼ 1",
            },
            {
                "rank": 6,
                "company": "JMW Solicitors",
                "location": "Manchester",
                "avg_days": 85,
                "response": "12 hrs",
                "comp_pct": "87%",
                "rating": 4.0,
                "txns": 142,
                "movement": "▼ 2",
            },
        ],
    },
    {
        "tab_id": "mortgage",
        "title": "Mortgage Leaderboard",
        "subtitle": "Ranked by average transaction time",
        "metric_note": (
            "Average days reflects typical contribution to transaction time from "
            "mortgage processing on our sample (demo data)."
        ),
        "rows": [
            {
                "rank": 1,
                "company": "L&C Mortgages",
                "location": "Nationwide (online)",
                "avg_days": 18,
                "response": "2 hrs",
                "comp_pct": "97%",
                "rating": 4.9,
                "txns": 342,
                "movement": "—",
            },
            {
                "rank": 2,
                "company": "Mortgage Advice Bureau",
                "location": "Lancaster",
                "avg_days": 21,
                "response": "3 hrs",
                "comp_pct": "95%",
                "rating": 4.7,
                "txns": 289,
                "movement": "▲ 1",
            },
            {
                "rank": 3,
                "company": "Habito",
                "location": "Nationwide (online)",
                "avg_days": 24,
                "response": "1 hr",
                "comp_pct": "92%",
                "rating": 4.5,
                "txns": 198,
                "movement": "▼ 1",
            },
            {
                "rank": 4,
                "company": "Alexander Hall",
                "location": "Preston",
                "avg_days": 26,
                "response": "4 hrs",
                "comp_pct": "94%",
                "rating": 4.6,
                "txns": 156,
                "movement": "▲ 2",
            },
            {
                "rank": 5,
                "company": "John Charcol",
                "location": "Nationwide",
                "avg_days": 29,
                "response": "6 hrs",
                "comp_pct": "90%",
                "rating": 4.3,
                "txns": 231,
                "movement": "▼ 1",
            },
            {
                "rank": 6,
                "company": "Trinity Financial",
                "location": "London, remote",
                "avg_days": 32,
                "response": "5 hrs",
                "comp_pct": "91%",
                "rating": 4.4,
                "txns": 178,
                "movement": "—",
            },
        ],
    },
    {
        "tab_id": "surveyors",
        "title": "Surveyor Leaderboard",
        "subtitle": "Ranked by average time to report",
        "metric_note": (
            "Average days is from instruction to report delivered (demo data)."
        ),
        "rows": [
            {
                "rank": 1,
                "company": "SDL Surveying",
                "location": "Lancashire wide",
                "avg_days": 52,
                "response": "2 hrs",
                "comp_pct": "98%",
                "rating": 4.8,
                "txns": 312,
                "movement": "▲ 1",
            },
            {
                "rank": 2,
                "company": "e.surv",
                "location": "Nationwide",
                "avg_days": 64,
                "response": "4 hrs",
                "comp_pct": "96%",
                "rating": 4.5,
                "txns": 487,
                "movement": "▼ 1",
            },
            {
                "rank": 3,
                "company": "Hollis & Associates",
                "location": "Lancaster, Morecambe",
                "avg_days": 73,
                "response": "3 hrs",
                "comp_pct": "97%",
                "rating": 4.7,
                "txns": 89,
                "movement": "▲ 1",
            },
            {
                "rank": 4,
                "company": "Rook Matthews Sayer",
                "location": "North West",
                "avg_days": 86,
                "response": "4 hrs",
                "comp_pct": "94%",
                "rating": 4.4,
                "txns": 145,
                "movement": "—",
            },
            {
                "rank": 5,
                "company": "Countrywide Surveying",
                "location": "Nationwide",
                "avg_days": 108,
                "response": "8 hrs",
                "comp_pct": "92%",
                "rating": 4.2,
                "txns": 534,
                "movement": "▼ 2",
            },
        ],
    },
    {
        "tab_id": "removals",
        "title": "Removals Leaderboard",
        "subtitle": "Ranked by average days to confirm booking",
        "metric_note": (
            "Average days is from enquiry to booking confirmed (demo data)."
        ),
        "rows": [
            {
                "rank": 1,
                "company": "Bradshaw's Removals",
                "location": "Lancaster, Morecambe",
                "avg_days": 1,
                "response": "1 hr",
                "comp_pct": "99%",
                "rating": 4.9,
                "txns": 178,
                "movement": "—",
            },
            {
                "rank": 2,
                "company": "Fox Moving",
                "location": "Lancashire wide",
                "avg_days": 1,
                "response": "2 hrs",
                "comp_pct": "98%",
                "rating": 4.8,
                "txns": 234,
                "movement": "▲ 1",
            },
            {
                "rank": 3,
                "company": "Kiwi Movers",
                "location": "North West",
                "avg_days": 2,
                "response": "3 hrs",
                "comp_pct": "97%",
                "rating": 4.7,
                "txns": 156,
                "movement": "▼ 1",
            },
            {
                "rank": 4,
                "company": "Britannia Movers",
                "location": "Nationwide",
                "avg_days": 2,
                "response": "4 hrs",
                "comp_pct": "96%",
                "rating": 4.5,
                "txns": 312,
                "movement": "▲ 2",
            },
            {
                "rank": 5,
                "company": "AnyVan",
                "location": "Nationwide (online)",
                "avg_days": 1,
                "response": "1 hr",
                "comp_pct": "95%",
                "rating": 4.3,
                "txns": 567,
                "movement": "▼ 1",
            },
        ],
    },
]


# Section 2.5 — weighted forecast score (sum of points for non-null fields; total 100).
FORECAST_SCORE_WEIGHTS = (
    ("welcome_emails_sent", 5),
    ("protocol_forms_returned", 10),
    ("seller_forms_returned", 10),
    ("survey_instructed", 10),
    ("searches_ordered", 10),
    ("searches_received", 15),
    ("draft_contract_sent", 10),
    ("enquiries_raised", 15),
    ("enquiries_answered", 10),  # brief: enquiries_resolved
    ("exchange_target", 5),  # brief: exchange_date
)

# Six funnel rows: cumulative keys per stage, then bar colour (brief).
FUNNEL_STEPS = (
    ("Welcome", ("welcome_emails_sent",), "#1B3A5C"),
    (
        "Forms",
        ("protocol_forms_returned", "seller_forms_returned"),
        "#3D5A73",
    ),
    (
        "Searches",
        ("searches_ordered", "searches_received"),
        "#3d6b66",
    ),
    ("Survey", ("survey_instructed",), "#4A7C6F"),
    (
        "Enquiries",
        ("enquiries_raised", "enquiries_answered"),
        "#4A7C6F",
    ),
    ("Exchange", ("exchange_target",), "#C4704B"),
)


def _field_populated(p, key):
    v = p.get(key)
    if v is None:
        return False
    if isinstance(v, str) and not str(v).strip():
        return False
    return True


def _parse_iso_date(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s in ("\u2014", "-"):
        return None
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


_CARD_CHIP_DEFS = (
    ("Welcome", ("welcome_emails_sent",)),
    ("Forms", ("protocol_forms_returned", "seller_forms_returned")),
    ("Searches", ("searches_ordered",)),
    ("Survey", ("survey_instructed",)),
    ("Enquiries", ("enquiries_raised",)),
    ("Exchange", ("exchange_target",)),
)


def _enrich_property_card_display(p: dict, today: date, triggers: list | None):
    """Attach display-only fields for rich dashboard cards (read-only merged data)."""
    n_m = len(FORECAST_SCORE_WEIGHTS)
    filled = sum(1 for k, _w in FORECAST_SCORE_WEIGHTS if _field_populated(p, k))
    p["_milestones_filled"] = filled
    p["_milestones_pct"] = int(round(100.0 * filled / n_m)) if n_m else 0

    chips_raw = []
    for label, keys in _CARD_CHIP_DEFS:
        done = any(_field_populated(p, k) for k in keys)
        chips_raw.append((label, done))
    first_open = None
    for i, (_lb, dn) in enumerate(chips_raw):
        if not dn:
            first_open = i
            break
    chips = []
    for i, (label, dn) in enumerate(chips_raw):
        if dn:
            st = "done"
        elif first_open is not None and i == first_open:
            st = "current"
        else:
            st = "pending"
        chips.append({"label": label, "state": st})
    p["_milestone_chips"] = chips

    if triggers:
        p["_rail"] = "attention"
        t0 = triggers[0] if triggers else None
        p["_card_badge_text"] = (
            (t0.get("trigger_name") or "").strip() if t0 else ""
        ) or "Needs attention"
    elif p.get("_is_exchanged") or p.get("status") == "exchanged":
        p["_rail"] = "exchanged"
        p["_card_badge_text"] = "Exchanged"
    elif p.get("status") in ("stalled", "at-risk"):
        p["_rail"] = "attention"
        p["_card_badge_text"] = (
            (p.get("alert") or "").strip()[:80]
            if p.get("alert")
            else (p.get("status_label") or "Needs attention").replace("_", " ")
        )
    elif p.get("status") == "on-track":
        p["_rail"] = "on-track"
        p["_card_badge_text"] = "On track"
    else:
        p["_rail"] = "default"
        p["_card_badge_text"] = (p.get("status_label") or "Status").title()

    sub_parts = []
    pt = p.get("_property_type")
    if pt and str(pt).strip() and str(pt).strip() != "\u2014":
        sub_parts.append(str(pt).strip())
    beds = p.get("_beds")
    if beds is not None and str(beds).strip() != "":
        try:
            b = int(beds)
            sub_parts.append(f"{b} bed{'s' if b != 1 else ''}")
        except (TypeError, ValueError):
            pass
    od = _parse_iso_date(p.get("offer_date") or p.get("_date_agreed"))
    if od:
        day = str(od.day)
        sub_parts.append(f"SSTC {day} {od.strftime('%b %Y')}")
    if sub_parts:
        p["_card_subtitle"] = " · ".join(sub_parts)
    else:
        p["_card_subtitle"] = ""

    offer_d = _parse_iso_date(p.get("offer_date") or p.get("_date_agreed"))
    comp_d = _parse_iso_date(p.get("completion_target"))
    if offer_d and comp_d:
        td = (comp_d - offer_d).days
        p["_card_target_days"] = str(td)
        p["_card_target_warn"] = td > 90
        p["_card_target_missing"] = False
    else:
        p["_card_target_days"] = ""
        p["_card_target_warn"] = False
        p["_card_target_missing"] = True

    initials = ""
    nm = (p.get("_negotiator_name") or "").strip()
    si = (p.get("_staff_initials") or "").strip()
    if si and si != "\u2014":
        initials = si.upper()[:4]
    elif nm:
        parts = nm.split()
        if len(parts) >= 2:
            initials = (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            initials = parts[0][:2].upper()
    p["_card_neg_initials"] = initials
    p["_card_neg_name"] = nm if nm else ""


def _pipeline_fee_gbp(p: dict) -> float:
    """Commission for pipeline £ totals: agreed_fee when set, else CRM fee (_fee)."""
    for key in ("agreed_fee", "_fee"):
        v = p.get(key)
        if v is None:
            continue
        if isinstance(v, str) and not str(v).strip():
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return 0.0


def _milestone_forecast_score(p):
    """0–100: sum of brief weights for populated progression fields."""
    return sum(
        w for k, w in FORECAST_SCORE_WEIGHTS if _field_populated(p, k)
    )


def _fmt_gbp_k(amount: float) -> str:
    """Display GBP in £Xk (thousands), no spurious decimals."""
    k = amount / 1000.0
    if k == 0:
        return "£0k"
    r = round(k, 1)
    if abs(r - round(r)) < 0.001:
        return f"£{int(round(r)):,}k"
    return f"£{r:,.1f}k"


def _first_of_next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _add_months_first(d: date, months: int) -> date:
    """d is always the 1st of a month; return 1st of month d + months."""
    y, m = d.year, d.month + months
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    return date(y, m, 1)


def _fee_bar_month_offset(score: int) -> int:
    """Map score band to one of five fee-chart month columns (0 = earliest)."""
    if score >= 70:
        return 0
    if score >= 45:
        return 1
    if score >= 25:
        return 2
    if score >= 12:
        return 3
    return 4


def _bucket_stats(items):
    fee_sum = sum(float(p.get("_pipe_fee") or 0) for p in items)
    return {"count": len(items), "fee": int(round(fee_sum))}


def _build_pipeline_forecast(properties, today, needs_attention_count):
    """
    Read-only forecast from merged live rows (EATOC + progression overlay).
    Uses milestone fill scoring (section 2.5); does not use completion_target
    for date bucketing. Never writes to sales_pipeline or sales_progression.
    """
    active = [p for p in properties if not p.get("_is_exchanged")]
    active_n = len(active)
    pipeline_value = sum(float(p.get("_pipe_fee") or 0) for p in active)

    if active_n == 0:
        badge_text = "No active pre-exchange cases on the board"
        badge_caution = False
    else:
        na_ratio = needs_attention_count / active_n
        if needs_attention_count == 0:
            badge_text = "Pipeline clear — nothing flagged for attention"
            badge_caution = False
        elif na_ratio <= 0.2:
            badge_text = "Few cases need attention"
            badge_caution = False
        else:
            badge_text = (
                f"{needs_attention_count} case{'s' if needs_attention_count != 1 else ''} "
                "need attention"
            )
            badge_caution = True

    anchor = _first_of_next_month(today)
    fee_month_starts = [_add_months_first(anchor, i) for i in range(5)]
    fee_labels = [d.strftime("%b") for d in fee_month_starts]
    fee_totals = [0.0] * 5
    for p in active:
        sc = _milestone_forecast_score(p)
        idx = _fee_bar_month_offset(sc)
        fee_totals[idx] += float(p.get("_pipe_fee") or 0.0)

    mx_fee = max(fee_totals) if fee_totals else 0.0
    mx_div = mx_fee if mx_fee > 0 else 1.0
    fee_bars = []
    for i, lab in enumerate(fee_labels):
        f = fee_totals[i]
        fee_bars.append(
            {
                "label": lab,
                "fee": int(round(f)),
                "h_pct": max(6, int(round(100.0 * f / mx_div))),
                "remainder": i >= 3,
            }
        )

    on_track_n = max(0, active_n - needs_attention_count)
    likely_30 = [p for p in active if _milestone_forecast_score(p) >= 70]
    n_30 = len(likely_30)
    val_30 = sum(float(p.get("_pipe_fee") or 0.0) for p in likely_30)

    if active_n:
        avg_days_active = int(
            round(
                sum(int(p.get("_bucket_days") or 0) for p in active)
                / float(active_n)
            )
        )
        on_track_pct = int(round(100.0 * on_track_n / float(active_n)))
    else:
        avg_days_active = 0
        on_track_pct = 0

    total_pop = sum(
        sum(1 for k, _w in FORECAST_SCORE_WEIGHTS if _field_populated(p, k))
        for p in active
    )
    milestone_sparse = active_n > 0 and total_pop == 0

    kpi_forecast_sub = (
        "No milestones recorded yet"
        if (n_30 == 0 and val_30 == 0 and milestone_sparse)
        else f"{n_30} likely completion{'s' if n_30 != 1 else ''}"
    )

    kpi_cards = [
        {
            "label": "Pipeline value",
            "value": _fmt_gbp_k(float(pipeline_value)),
            "sub": f"{active_n} {'property' if active_n == 1 else 'properties'}",
        },
        {
            "label": "30-day forecast",
            "value": _fmt_gbp_k(float(val_30)),
            "sub": kpi_forecast_sub,
        },
        {
            "label": "Avg days active",
            "value": str(avg_days_active),
            "sub": "Target: sub-90",
        },
        {
            "label": "On track",
            "value": f"{on_track_pct}%",
            "sub": f"{needs_attention_count} need attention",
        },
    ]

    funnel = []
    denom = max(1, active_n)
    cum_funnel_keys = []
    for label, keys, fill in FUNNEL_STEPS:
        cum_funnel_keys.extend(keys)
        reached = sum(
            1
            for p in active
            if all(_field_populated(p, kk) for kk in cum_funnel_keys)
        )
        pct = int(round(100.0 * reached / denom))
        funnel.append({"label": label, "pct": pct, "fill": fill})

    band_high = [p for p in active if _milestone_forecast_score(p) >= 70]
    band_mid = [
        p for p in active if 45 <= _milestone_forecast_score(p) <= 69
    ]
    band_low = [
        p for p in active if 25 <= _milestone_forecast_score(p) <= 44
    ]
    band_rem = [p for p in active if _milestone_forecast_score(p) <= 24]
    bh, bm, bl, br = (
        _bucket_stats(band_high),
        _bucket_stats(band_mid),
        _bucket_stats(band_low),
        _bucket_stats(band_rem),
    )

    month_cards_empty = bh["count"] + bm["count"] + bl["count"] == 0
    month_note_alt = "Properties will appear here as milestones are recorded."
    month_cards = [
        {
            "title": "Month 1 completion forecast",
            "count": bh["count"],
            "fee": bh["fee"],
            "note": month_note_alt if month_cards_empty else "Milestone score 70–100 (first fee column).",
        },
        {
            "title": "Month 2 completion forecast",
            "count": bm["count"],
            "fee": bm["fee"],
            "note": month_note_alt if month_cards_empty else "Milestone score 45–69 (second fee column).",
        },
        {
            "title": "Month 3 completion forecast",
            "count": bl["count"],
            "fee": bl["fee"],
            "note": (
                month_note_alt
                if month_cards_empty
                else (
                    "Milestone score 25–44 (third fee column). "
                    f"Remainder 0–24: {br['count']} case"
                    f"{'s' if br['count'] != 1 else ''}, £{br['fee']:,} pipeline fee — "
                    "fourth and fifth fee columns."
                )
            ),
        },
    ]

    fee_chart_subtitle = (
        f"{fee_labels[0]}–{fee_labels[4]} {anchor.year} — fees by milestone progress"
    )

    fee_primary_zero = active_n > 0 and sum(fee_totals[i] for i in range(3)) == 0

    funnel_all_zero = active_n > 0 and all(
        row["pct"] == 0 for row in funnel
    )

    subtitle = (
        "Projected completions and fee income based on milestone progress"
    )

    return {
        "subtitle": subtitle,
        "fee_chart_subtitle": fee_chart_subtitle,
        "kpi_cards": kpi_cards,
        "fee_bars": fee_bars,
        "funnel": funnel,
        "month_cards": month_cards,
        "badge_text": badge_text,
        "badge_caution": badge_caution,
        "show_fee_chart_hint": fee_primary_zero,
        "show_funnel_hint": funnel_all_zero,
    }


def _normalize_addr(addr):
    """Normalize address for fuzzy matching between tables."""
    return " ".join(addr.lower().replace(",", " ").replace(".", " ").split())


def _match_pipeline(prog_addr, pipe_lookup, pipe_norm_keys):
    """Find matching pipeline record for a progression address."""
    norm = _normalize_addr(prog_addr)
    # Exact match
    if norm in pipe_lookup:
        return pipe_lookup[norm]
    # Substring: progression addr contained in pipeline addr or vice versa
    for key in pipe_norm_keys:
        if norm in key or key in norm:
            return pipe_lookup[key]
    # First-word match (e.g. "Greyber" vs "The Farmhouse  Grayber")
    words = norm.split()
    first = words[0] if words else ""
    if len(first) > 3:
        for key in pipe_norm_keys:
            if first in key:
                return pipe_lookup[key]
    # Try second word if first is a number (e.g. "14 howard park")
    if len(words) > 1 and words[0].isdigit():
        fragment = " ".join(words[:2])
        for key in pipe_norm_keys:
            if fragment in key:
                return pipe_lookup[key]
    return None


def _merge_sales_pipeline_for_dashboard(properties, pipe_rows, today):
    """Attach sales_pipeline row by normalised address; exchanged + bucket days."""
    from utils.address import normalise_address

    pipe_by_norm = {}
    for row in pipe_rows or []:
        k = normalise_address(row.get("property_address") or "")
        if k:
            pipe_by_norm[k] = row
    for p in properties:
        k = normalise_address(p.get("address") or "")
        pr = pipe_by_norm.get(k)
        p["_pipeline_row"] = pr
        sid = pr.get("id") if pr else None
        p["_sales_pipeline_id"] = str(sid) if sid else None

        if pr:
            cs = (pr.get("chain_status") or "stable").strip().lower()
            p["chain_status"] = (
                cs if cs in ("stable", "at_risk", "broken") else "stable"
            )
            la = pr.get("local_authority")
            if la is not None and str(la).strip():
                p["local_authority"] = str(la).strip()
            cp = pr.get("current_price")
            if cp is not None and str(cp).strip() != "":
                try:
                    p["price"] = int(float(cp))
                except (TypeError, ValueError):
                    pass
            af = pr.get("agreed_fee")
            if af is not None and str(af).strip() != "":
                try:
                    p["agreed_fee"] = float(af)
                except (TypeError, ValueError):
                    pass
            fe = pr.get("fee")
            if fe is not None and str(fe).strip() != "":
                try:
                    p["_fee"] = float(fe)
                except (TypeError, ValueError):
                    pass
        else:
            p.setdefault("chain_status", "stable")
            p.setdefault("local_authority", "")

        raw_ex = (p.get("_raw_status") or "").lower() == "exchanged"
        pst = (pr.get("status") or "") if pr else ""
        pipe_ex = "exchanged" in pst.lower()
        p["_is_exchanged"] = bool(raw_ex or pipe_ex)

        bdays = None
        ts = (pr or {}).get("created_at") or p.get("_eatoc_created_at")
        if ts:
            try:
                d0 = datetime.strptime(str(ts)[:10], "%Y-%m-%d").date()
                bdays = max(0, (today - d0).days)
            except Exception:
                pass
        if bdays is None:
            try:
                bdays = int(p.get("duration_days") or 0)
            except (TypeError, ValueError):
                bdays = 0
        p["_bucket_days"] = bdays


def _build_live_dashboard_data():
    """EATOC list + Supabase progression, pipeline, images, needs-attention engine.

    Pipeline Forecast aggregates read-only fields only; it never mutates
    sales_pipeline or sales_progression (see ARCHITECTURE.md).
    """
    from routes.crm import _map_live_properties
    from utils.address import normalise_address
    from utils.needs_attention import get_needs_attention

    properties, err = _map_live_properties()
    if err:
        raise RuntimeError(err) from None

    img_rows = fetch_property_images()
    chain_rows = fetch_chain_links()
    pipe_rows = fetch_sales_pipeline() or []

    _img_by_addr = {}
    _propid_by_addr = {}
    for row in img_rows:
        prop_id = row.get("id")
        addr = _normalize_addr(row.get("address") or "")
        if addr and prop_id:
            _propid_by_addr[addr] = prop_id
        url = (row.get("image_url") or "").strip() or None
        if not url:
            urls = row.get("photo_urls") or []
            if isinstance(urls, list):
                for u in urls:
                    cand = (u or "").strip()
                    if cand:
                        url = cand
                        break
        if not url:
            continue
        if addr:
            _img_by_addr[addr] = url

    _chain_by_propid = {}
    for cl in chain_rows:
        pid = cl.get("property_id")
        if pid:
            _chain_by_propid.setdefault(pid, []).append(cl)
    _pos_order = {"above": 0, "below": 1}
    for pid in _chain_by_propid:
        _chain_by_propid[pid].sort(
            key=lambda x: _pos_order.get(x.get("chain_position", ""), 2)
        )

    today = date.today()
    _merge_sales_pipeline_for_dashboard(properties, pipe_rows, today)

    for p in properties:
        addr_norm = _normalize_addr(p.get("address") or "")
        pid = _propid_by_addr.get(addr_norm)
        p["chain_links"] = _chain_by_propid.get(pid or "", [])
        p.setdefault("activity", [])
        p["_pipe_fee"] = _pipeline_fee_gbp(p)
        if not (p.get("image_url") or "").strip():
            p["image_url"] = _img_by_addr.get(addr_norm, "")

    from db_portal import enrich_properties_with_portal_forms

    enrich_properties_with_portal_forms(properties)

    la_rows = fetch_local_authority_search_times()
    la_by_norm: dict[str, int] = {}
    for row in la_rows:
        name = (row.get("local_authority_name") or "").strip()
        if not name:
            continue
        k = normalise_address(name)
        if k:
            try:
                la_by_norm[k] = int(row.get("avg_turnaround_days") or 21)
            except (TypeError, ValueError):
                la_by_norm[k] = 21

    sv_rows = fetch_preferred_surveyors()
    surveyor_hint = None
    if sv_rows:
        r0 = sv_rows[0]
        nm = (r0.get("surveyor_name") or "").strip()
        fm = (r0.get("surveyor_firm") or "").strip()
        surveyor_hint = f"{nm} ({fm})" if nm and fm else (nm or fm or None)

    na_candidates = [p for p in properties if not p.get("_is_exchanged")]
    na_raw = get_needs_attention(
        na_candidates,
        la_by_norm,
        surveyor_hint=surveyor_hint,
        today=today,
    )
    needs_attention_items = []
    for it in na_raw:
        it["property"]["_needs_attention_triggers"] = it["triggers"]
        needs_attention_items.append(
            {"property": it["property"], "triggers": it["triggers"]}
        )

    any_red_na = any(
        t["severity"] == "red" for it in na_raw for t in it["triggers"]
    )

    b0, b1, b2 = [], [], []
    for p in properties:
        if p.get("_is_exchanged"):
            continue
        d = int(p.get("_bucket_days") or 0)
        if d <= 30:
            b0.append(p)
        elif d <= 90:
            b1.append(p)
        else:
            b2.append(p)

    def _make_section(sid, icon, title, subtitle, border, items):
        visible = items[:3]
        hidden = items[3:]
        avg = int(sum(p["progress"] for p in items) / len(items)) if items else 0
        color = (
            "#962D3E"
            if border == "stalled-banner"
            else "#D4940A"
            if border == "amber-banner"
            else "#C5D93A"
        )
        return {
            "id": sid,
            "icon": icon,
            "title": title,
            "subtitle": subtitle,
            "count": len(items),
            "avg_progress": avg,
            "avg_color": color,
            "border_class": border,
            "visible": visible,
            "hidden": hidden,
            "extra_count": 0,
        }

    sections = [
        _make_section(
            "bucket-0-30",
            "\U0001F4C5",
            "One Month Remaining",
            "Properties added in the last 30 days",
            "green-banner",
            b0,
        ),
        _make_section(
            "bucket-31-90",
            "\U0001F4CA",
            "Two to Three Months",
            "Properties added 31–90 days ago",
            "blue-banner",
            b1,
        ),
        _make_section(
            "bucket-90-plus",
            "\U0001F4C8",
            "Three Months and Over",
            "Properties added over 90 days ago",
            "amber-banner",
            b2,
        ),
    ]

    exchanged_count = sum(1 for p in properties if p.get("_is_exchanged"))
    active_props = [p for p in properties if not p.get("_is_exchanged")]
    active_count = len(active_props)
    needs_attention_count = len(needs_attention_items)
    on_track_count = max(0, active_count - needs_attention_count)
    pipeline_value = sum(float(p.get("_pipe_fee") or 0.0) for p in active_props)

    stats = {
        "active": active_count,
        "on_track": on_track_count,
        "needs_attention": needs_attention_count,
        "exchanged": exchanged_count,
        "pipeline_value": int(round(pipeline_value)),
        "needs_header_severity": "red" if any_red_na else ("amber" if na_raw else "none"),
    }

    pipeline = _build_pipeline_forecast(
        properties, today, needs_attention_count
    )

    na_triggers_by_id = {}
    for it in needs_attention_items:
        pid = it["property"].get("id")
        if pid is not None:
            na_triggers_by_id[pid] = it["triggers"]
    for p in properties:
        _enrich_property_card_display(
            p, today, na_triggers_by_id.get(p.get("id"))
        )

    return properties, sections, stats, pipeline, needs_attention_items


@dashboard_bp.route("/")
def dashboard():
    try:
        properties, sections, stats, pipeline, needs_attention_items = (
            _build_live_dashboard_data()
        )
    except Exception as e:
        # Fallback: show error
        return f"<h2>Error loading live data</h2><pre>{e}</pre>", 500

    return render_template_string(
        DASHBOARD_HTML,
        sections=sections,
        needs_attention_items=needs_attention_items,
        stats=stats,
        pipeline=pipeline,
        properties_json=json.dumps(properties, default=str),
        leaderboard_tabs=LEADERBOARD_TABS,
    )

