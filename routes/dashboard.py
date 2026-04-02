import json
from datetime import datetime

from flask import Blueprint, render_template_string

from db_supabase import (
    fetch_chain_links,
    fetch_property_images,
    fetch_sales_pipeline,
    fetch_sales_progression,
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
  --navy:#0f1b2d;--navy-lt:#162236;--navy-md:#1c2e4a;--navy-card:#182842;
  --lime:#c4e233;--lime-dk:#a3bf1a;
  --red:#e25555;--red-chip:#e84545;
  --amber:#e88a3a;--amber-chip:#e8873a;
  --green:#27ae60;--green-chip:#2fa868;
  --blue:#3b82f6;
  --white:#ffffff;--off-white:#f4f6f9;
  --txt:#1e293b;--txt-mid:#475569;--txt-light:#94a3b8;
  --card-shadow:0 2px 12px rgba(0,0,0,.08);
  --t:.22s ease;
}
html{font-size:15px;scroll-behavior:smooth}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--off-white);color:var(--txt);min-height:100vh}

/* ═══ HERO ════════════════════════════════════════════════ */
.hero{position:relative;width:100%;height:480px;overflow:hidden;background:var(--navy)}
.hero-img{width:100%;height:100%;object-fit:cover;display:block}

/* NUVU badge — top right */
.hero-badge{
  position:absolute;top:28px;right:32px;
  background:rgba(15,27,45,.88);backdrop-filter:blur(12px);
  border-radius:14px;padding:18px 28px 14px;
  display:flex;flex-direction:column;align-items:center;
  border:1px solid rgba(255,255,255,.08);
}
.hero-badge-top{display:flex;align-items:center;gap:14px}
.hero-badge img{width:48px;height:48px;border-radius:10px}
.hero-badge-top h1{font-size:2rem;font-weight:900;color:var(--white);letter-spacing:12px;line-height:1;margin:0;text-indent:12px}
.hero-badge-strapline{font-size:.6rem;color:var(--lime);text-transform:uppercase;letter-spacing:3px;font-weight:600;margin-top:8px;text-align:center;white-space:nowrap}

/* Stats overlay — floating rounded card over hero */
.hero-stats{
  position:absolute;bottom:24px;left:50%;transform:translateX(-50%);
  width:calc(100% - 64px);max-width:1400px;
  background:#1a2332;
  border-radius:16px;
  box-shadow:0 8px 32px rgba(0,0,0,.3);
  border:1px solid rgba(255,255,255,.08);
  display:flex;justify-content:center;padding:0;
}
.hs{
  flex:1;max-width:220px;text-align:center;padding:22px 16px;
  border-right:1px solid rgba(255,255,255,.08);
  cursor:pointer;transition:background var(--t);
}
.hs:last-child{border-right:none}
.hs:hover{background:rgba(255,255,255,.05);border-radius:4px}
.hs-val{font-size:2.1rem;font-weight:900;color:var(--white);line-height:1}
.hs-lbl{font-size:.68rem;text-transform:uppercase;letter-spacing:1.8px;color:rgba(255,255,255,.55);margin-top:6px;font-weight:600}

/* ═══ PIPELINE FORECAST ═══════════════════════════════════ */
.pipeline-section{
  background:var(--navy);padding:36px 40px 40px;cursor:pointer;
  transition:background .2s ease;
}
.pipeline-section:hover{background:#0d1826}
.pipeline-header{
  display:flex;justify-content:space-between;align-items:flex-start;
  max-width:1280px;margin:0 auto 24px;
}
.pipeline-title{font-size:1.25rem;font-weight:800;color:var(--white);display:flex;align-items:center;gap:10px}
.pipeline-sub{font-size:.82rem;color:rgba(255,255,255,.45);margin-top:4px}
.ahead-badge{
  background:rgba(196,226,51,.12);color:var(--lime);
  padding:7px 16px;border-radius:20px;font-size:.82rem;font-weight:700;
  display:flex;align-items:center;gap:6px;
}
.pipeline-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:20px;
  max-width:1280px;margin:0 auto;
}
.pipe-card{
  background:var(--navy-lt);border:1px solid rgba(255,255,255,.06);
  border-radius:14px;padding:22px 24px;
}
.pipe-period{font-size:.68rem;text-transform:uppercase;letter-spacing:1.5px;color:rgba(255,255,255,.45);font-weight:600;margin-bottom:10px}
.pipe-count{font-size:2rem;font-weight:900;color:var(--white);line-height:1}
.pipe-value{font-size:1.05rem;font-weight:800;color:var(--lime);margin-top:4px}
.pipe-bar{width:100%;height:6px;border-radius:3px;background:rgba(255,255,255,.1);margin-top:14px;overflow:hidden}
.pipe-bar-fill{height:100%;border-radius:3px;background:var(--lime)}
.pipe-confidence{font-size:.75rem;color:rgba(255,255,255,.4);margin-top:8px}

/* ═══ MAIN CONTENT ════════════════════════════════════════ */
.content{max-width:1280px;margin:0 auto;padding:0 32px 60px}

/* ═══ SECTION HEADERS ═════════════════════════════════════ */
.section-banner{
  display:flex;justify-content:space-between;align-items:center;
  padding:28px 0 20px;
  border-left:4px solid transparent;
  padding-left:20px;margin-left:-24px;
}
.section-banner.stalled-banner{border-left-color:var(--red)}
.section-banner.risk-banner{border-left-color:var(--amber)}
.section-banner.green-banner{border-left-color:var(--green)}
.section-banner.blue-banner{border-left-color:var(--blue)}
.section-banner.amber-banner{border-left-color:var(--amber)}
.section-banner-left h2{font-size:1.3rem;font-weight:800;color:var(--txt);display:flex;align-items:center;gap:10px}
.section-banner-left p{font-size:.88rem;color:var(--txt-light);margin-top:2px}

/* Section avg progress bar */
.section-avg{display:flex;align-items:center;gap:12px}
.avg-label{font-size:.68rem;text-transform:uppercase;letter-spacing:1px;color:var(--txt-light);font-weight:600;white-space:nowrap}
.avg-bar-wrap{display:flex;align-items:center;gap:8px}
.avg-bar{width:120px;height:8px;border-radius:4px;background:#e8ecf1;overflow:hidden}
.avg-bar-fill{height:100%;border-radius:4px;transition:width .4s ease}
.avg-pct{font-size:.85rem;font-weight:800;color:var(--txt);min-width:35px}

/* ═══ CARD GRID ═══════════════════════════════════════════ */
.card-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:24px;
  margin-bottom:12px;
}

/* ═══ PROPERTY CARD — white, photo top ════════════════════ */
.prop-card{
  background:var(--white);border-radius:16px;overflow:hidden;
  box-shadow:var(--card-shadow);cursor:pointer;
  transition:all var(--t);border:1px solid #e8ecf1;
}
.prop-card:hover{
  transform:translateY(-4px);
  box-shadow:0 12px 32px rgba(0,0,0,.12);
}

/* photo area */
.card-photo{
  height:160px;position:relative;overflow:hidden;
  display:flex;align-items:center;justify-content:center;
}
.card-photo-bg{width:100%;height:100%;object-fit:cover}
.card-chip{
  position:absolute;top:12px;right:12px;
  padding:5px 14px;border-radius:6px;
  font-size:.68rem;font-weight:800;letter-spacing:.8px;color:var(--white);
}
.chip-stalled{background:var(--red-chip)}
.chip-at-risk{background:var(--amber-chip)}
.chip-on-track{background:var(--green-chip)}

/* card body */
.card-body{padding:18px 22px 20px}
.card-name{font-size:1.05rem;font-weight:700;color:var(--txt);margin-bottom:14px}

/* progress + duration row */
.card-progress-row{display:flex;align-items:center;gap:16px;margin-bottom:16px}

/* SVG progress ring */
.ring-wrap{position:relative;width:64px;height:64px;flex-shrink:0}
.ring-wrap svg{width:64px;height:64px;transform:rotate(-90deg)}
.ring-bg{fill:none;stroke:#e2e8f0;stroke-width:5}
.ring-fg{fill:none;stroke-width:5;stroke-linecap:round}
.ring-fg.clr-stalled{stroke:var(--red)}
.ring-fg.clr-at-risk{stroke:var(--amber)}
.ring-fg.clr-on-track{stroke:var(--lime)}
.ring-pct{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-size:.8rem;font-weight:800;color:var(--txt);
}

/* duration block */
.card-duration .dur-label{font-size:.65rem;text-transform:uppercase;letter-spacing:1.2px;color:var(--txt-light);font-weight:600}
.card-duration .dur-val{font-size:1.3rem;font-weight:800;color:var(--txt);line-height:1.2}
.card-duration .dur-target{font-size:.78rem;color:var(--txt-light)}

/* checklist */
.card-checks{display:flex;flex-direction:column;gap:6px}
.chk{display:flex;align-items:center;gap:8px;font-size:.85rem}
.chk-done{color:var(--green);font-weight:600}
.chk-pending{color:var(--txt-light)}
.chk-icon{width:20px;height:20px;border-radius:4px;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:.7rem}
.chk-icon.done{background:var(--green);color:#fff}
.chk-icon.pending{background:#e8ecf1;border:1.5px solid #cbd5e1;color:transparent}

/* ═══ SHOW MORE ═══════════════════════════════════════════ */
.show-more-btn{
  display:flex;align-items:center;justify-content:center;gap:8px;
  width:100%;padding:14px;margin:8px 0 24px;
  background:var(--white);border:1px dashed #cbd5e1;border-radius:12px;
  color:var(--txt-mid);font-size:.88rem;font-weight:600;cursor:pointer;
  transition:all var(--t);
}
.show-more-btn:hover{border-color:var(--green);color:var(--green);background:#f0fdf4}
.show-more-btn svg{transition:transform var(--t)}
.show-more-btn.expanded svg{transform:rotate(180deg)}
.show-more-panel{display:none;margin-bottom:24px}
.show-more-panel.open{display:block}

/* extra summary (for larger counts) */
.extra-summary{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 20px;margin-top:16px;
  background:var(--white);border:1px solid #e8ecf1;border-radius:12px;
  color:var(--txt-mid);font-size:.88rem;
}
.extra-note{font-size:.78rem;color:var(--txt-light);font-style:italic}

/* ═══ MODAL ═══════════════════════════════════════════════ */
.modal-overlay{
  display:none;position:fixed;inset:0;
  background:rgba(0,0,0,.55);backdrop-filter:blur(4px);
  z-index:2000;align-items:center;justify-content:center;padding:20px;
}
.modal-overlay.open{display:flex}
.modal{
  background:var(--white);border-radius:18px;
  width:100%;max-width:620px;max-height:85vh;overflow-y:auto;
  box-shadow:0 30px 80px rgba(0,0,0,.3);animation:modalIn .25s ease;
  color:var(--txt);
}
@keyframes modalIn{from{opacity:0;transform:translateY(20px) scale(.97)}to{opacity:1;transform:translateY(0) scale(1)}}
.modal::-webkit-scrollbar{width:5px}
.modal::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:3px}

/* modal header */
.m-hdr{padding:18px 22px 0;display:flex;justify-content:space-between;align-items:flex-start}
.m-hdr h2{font-size:1.15rem;font-weight:800}
.m-hdr .m-loc{font-size:.8rem;color:var(--txt-light);margin-top:2px}
.m-price{font-size:1.2rem;font-weight:800;color:var(--green)}
.m-close{
  width:34px;height:34px;border-radius:50%;
  background:#f1f5f9;border:1px solid #e2e8f0;
  color:var(--txt-mid);font-size:1rem;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  transition:all var(--t);margin-left:10px;flex-shrink:0;
}
.m-close:hover{background:var(--red);color:#fff;border-color:var(--red)}

/* progress bar */
.m-prog{padding:12px 22px 0}
.m-prog-bar{width:100%;height:6px;border-radius:3px;background:#e8ecf1;overflow:hidden}
.m-prog-fill{height:100%;border-radius:4px;transition:width .4s ease}
.m-prog-fill.clr-stalled{background:var(--red)}
.m-prog-fill.clr-at-risk{background:var(--amber)}
.m-prog-fill.clr-on-track{background:var(--green)}
.m-prog-labels{display:flex;justify-content:space-between;font-size:.65rem;color:var(--txt-light);margin-top:4px}

/* body */
.m-body{padding:10px 22px 0}
.m-div{border:none;border-top:1px solid #e8ecf1;margin:10px 0}

/* alert */
.m-alert{padding:10px 14px;border-radius:8px;margin-bottom:10px;font-size:.82rem;line-height:1.45;display:flex;gap:8px;align-items:flex-start}
.m-alert svg{flex-shrink:0;margin-top:2px}
.m-alert-red{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca}
.m-alert-amber{background:#fffbeb;color:#92400e;border:1px solid #fde68a}
.m-alert-green{background:#f0fdf4;color:#166534;border:1px solid #bbf7d0}

/* next action */
.m-next{background:#f8fafc;border:1px solid #e8ecf1;border-radius:8px;padding:10px 14px;margin-bottom:10px}
.m-next-lbl{font-size:.65rem;text-transform:uppercase;letter-spacing:1px;color:var(--green);font-weight:700;margin-bottom:3px}
.m-next-txt{font-size:.82rem;color:var(--txt);line-height:1.45}

/* action buttons */
.m-actions{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
.m-btn{flex:1;min-width:100px;padding:9px 12px;border-radius:8px;font-size:.78rem;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px;transition:all var(--t);border:none}
.m-btn svg{width:15px;height:15px}
.m-btn-call{background:var(--lime);color:var(--navy)}
.m-btn-call:hover{background:var(--lime-dk)}
.m-btn-done{background:var(--green);color:#fff}
.m-btn-done:hover{background:#219a52}
.m-btn-outline{background:transparent;color:var(--txt);border:1px solid #d1d5db}
.m-btn-outline:hover{border-color:var(--green);color:var(--green)}

/* milestones */
.m-ms h3{font-size:.82rem;font-weight:700;margin-bottom:6px;display:flex;align-items:center;gap:8px}
.ms-list{display:flex;flex-direction:column}
.ms-item{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #f1f5f9;font-size:.78rem}
.ms-item:last-child{border-bottom:none}
.ms-ic{width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:.6rem}
.ms-ic.done{background:var(--green);color:#fff}
.ms-ic.pending{background:#f1f5f9;border:2px solid #cbd5e1;color:transparent}
.ms-ic.na{background:#f1f5f9;color:var(--txt-light);font-size:.55rem;font-weight:700}
.ms-lb{color:var(--txt);flex:1}
.ms-lb.done-lb{color:var(--txt-light);text-decoration:line-through}
.ms-date{font-size:.7rem;color:var(--txt-light);margin-left:auto;white-space:nowrap}
.ms-edit-btn{background:none;border:1px solid #d1d5db;border-radius:5px;padding:2px 8px;font-size:.65rem;color:var(--txt-mid);cursor:pointer;transition:all var(--t);flex-shrink:0}
.ms-edit-btn:hover{border-color:var(--green);color:var(--green)}
.ms-edit-form{display:flex;align-items:center;gap:6px;margin-left:auto;flex-shrink:0}
.ms-edit-form input[type=date]{font-size:.72rem;padding:2px 6px;border:1px solid #d1d5db;border-radius:5px;color:var(--txt)}
.ms-edit-form button{padding:2px 8px;border-radius:5px;font-size:.65rem;font-weight:600;cursor:pointer;border:none}
.ms-save-btn{background:var(--green);color:#fff}
.ms-cancel-btn{background:#f1f5f9;color:var(--txt-mid)}
.ms-pending-lb{color:var(--txt-light);font-style:italic}

/* note editor */
.note-block{background:#f8fafc;border:1px solid #e8ecf1;border-radius:8px;padding:10px 14px;margin-bottom:8px}
.note-block-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.note-block-lbl{font-size:.68rem;text-transform:uppercase;letter-spacing:.8px;color:var(--txt-light);font-weight:600}
.note-edit-btn{background:none;border:1px solid #d1d5db;border-radius:5px;padding:2px 10px;font-size:.65rem;color:var(--txt-mid);cursor:pointer;transition:all var(--t)}
.note-edit-btn:hover{border-color:var(--green);color:var(--green)}
.note-block-txt{font-size:.82rem;line-height:1.5;color:var(--txt);white-space:pre-wrap}
.note-block-txt.empty{color:var(--txt-light);font-style:italic}
.note-textarea{width:100%;min-height:60px;font-size:.82rem;font-family:inherit;line-height:1.5;border:1px solid #d1d5db;border-radius:6px;padding:8px 10px;resize:vertical;color:var(--txt)}
.note-textarea:focus{outline:none;border-color:var(--green)}
.note-actions{display:flex;gap:6px;margin-top:6px}
.note-save-btn{background:var(--green);color:#fff;border:none;border-radius:5px;padding:4px 14px;font-size:.72rem;font-weight:600;cursor:pointer}
.note-cancel-btn{background:#f1f5f9;color:var(--txt-mid);border:none;border-radius:5px;padding:4px 14px;font-size:.72rem;cursor:pointer}

/* activity notes */
.act-item{background:#f8fafc;border:1px solid #e8ecf1;border-radius:8px;padding:8px 12px;margin-bottom:6px;font-size:.8rem;line-height:1.45;color:var(--txt)}
.act-idx{font-size:.65rem;text-transform:uppercase;letter-spacing:1px;color:var(--txt-light);font-weight:600}

/* expandable details */
.m-det-toggle{
  width:100%;background:#f8fafc;border:1px solid #e8ecf1;
  border-radius:8px;padding:10px 14px;margin-bottom:4px;
  color:var(--txt);font-size:.82rem;font-weight:600;cursor:pointer;
  display:flex;align-items:center;justify-content:space-between;transition:all var(--t);
}
.m-det-toggle:hover{border-color:var(--green)}
.m-det-toggle svg{transition:transform var(--t)}
.m-det-toggle.expanded svg{transform:rotate(180deg)}
.m-det-panel{max-height:0;overflow:hidden;transition:max-height .35s ease}
.m-det-panel.expanded{max-height:650px}
.m-det-inner{padding:14px 0 4px}
.det-grid{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px}
.d-r{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #f1f5f9;font-size:.75rem}
.d-r:last-child{border-bottom:none}
.d-l{color:var(--txt-light)}
.d-v{font-weight:600;color:var(--txt);text-align:right}
.d-full{grid-column:1/-1;padding:10px 0 2px}
.d-full-l{font-size:.7rem;text-transform:uppercase;letter-spacing:1px;color:var(--txt-light);margin-bottom:3px}
.d-full-v{font-size:.82rem;color:var(--txt);line-height:1.5}

.m-footer{padding:6px 22px 16px}

/* ═══ ANALYTICS MODAL ════════════════════════════════════ */
.analytics-chart{
  height:200px;background:linear-gradient(135deg,var(--navy-lt),var(--navy-md));
  border-radius:12px;display:flex;align-items:flex-end;justify-content:center;
  gap:20px;padding:24px 32px;margin-bottom:16px;
}
.analytics-chart .bar{
  width:40px;border-radius:6px 6px 0 0;background:var(--lime);opacity:.8;
  transition:opacity .2s;position:relative;
}
.analytics-chart .bar:hover{opacity:1}
.analytics-chart .bar span{
  position:absolute;top:-20px;left:50%;transform:translateX(-50%);
  font-size:.65rem;color:var(--lime);font-weight:700;white-space:nowrap;
}
.analytics-coming{text-align:center;color:var(--txt-light);font-size:.88rem;margin:12px 0 16px;font-style:italic}
.analytics-rows{display:flex;flex-direction:column;gap:8px}
.anal-row{
  display:flex;justify-content:space-between;align-items:center;
  padding:10px 14px;background:#f8fafc;border-radius:8px;border:1px solid #e8ecf1;
}
.anal-row-label{font-size:.85rem;font-weight:600;color:var(--txt)}
.anal-row-value{font-size:.82rem;color:var(--txt-mid)}

/* ═══ RESPONSIVE ══════════════════════════════════════════ */
@media(max-width:960px){.card-grid{grid-template-columns:repeat(2,1fr)}.pipeline-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:640px){
  .hero{height:320px}
  .hero-badge{top:16px;right:16px;padding:12px 18px}
  .hero-badge img{width:36px;height:36px}
  .hero-badge-text h1{font-size:1.3rem}
  .hs{padding:14px 10px}.hs-val{font-size:1.4rem}
  .pipeline-section{padding:24px 20px}
  .pipeline-grid,.card-grid{grid-template-columns:1fr}
  .content{padding:0 16px 40px}
  .section-banner{flex-direction:column;align-items:flex-start;gap:8px}
  .section-avg{margin-top:4px}
  .modal{border-radius:14px}
  .m-hdr,.m-body,.m-prog,.m-footer{padding-left:16px;padding-right:16px}
  .det-grid{grid-template-columns:1fr}
  .search-wrap{padding:10px 16px}
  .search-input{font-size:.95rem;padding:12px 14px 12px 48px}
}

/* ── Search bar ─────────────────────────────────────────── */
.search-wrap{
  position:sticky;top:0;z-index:90;
  background:var(--navy);
  padding:12px 40px;
  border-bottom:1px solid rgba(255,255,255,.08);
}
.search-input{
  width:100%;box-sizing:border-box;
  padding:14px 16px 14px 48px;
  font-size:1rem;font-family:inherit;
  background:var(--navy-lt);color:#fff;
  border:1px solid rgba(255,255,255,.12);border-radius:10px;
  outline:none;transition:border var(--t),box-shadow var(--t);
}
.search-input::placeholder{color:var(--txt-light)}
.search-input:focus{border-color:var(--lime);box-shadow:0 0 0 3px rgba(196,226,51,.15)}
.search-icon{
  position:absolute;left:14px;top:50%;transform:translateY(-50%);
  pointer-events:none;color:var(--txt-light);
}
.search-no-match{
  text-align:center;padding:32px 0;color:var(--txt-light);font-style:italic;display:none;
}

/* ═══ CHAIN DISPLAY ═══════════════════════════════════════ */
.chain-toggle{
  width:100%;background:#f8fafc;border:none;border-top:1px solid #e8ecf1;
  padding:10px 22px;color:var(--txt-mid);font-size:.78rem;font-weight:600;
  cursor:pointer;display:flex;align-items:center;justify-content:space-between;
  transition:all var(--t);
}
.chain-toggle:hover{background:#f0f4f8;color:var(--txt)}
.chain-toggle svg{transition:transform var(--t);flex-shrink:0}
.chain-toggle.expanded svg{transform:rotate(180deg)}
.chain-toggle .chain-lbl{display:flex;align-items:center;gap:6px}
.chain-panel{max-height:0;overflow:hidden;transition:max-height .35s ease}
.chain-panel.expanded{max-height:1200px}
.chain-inner{padding:12px 22px 16px}
.chain-diagram{display:flex;flex-direction:column;align-items:center;gap:0}
.chain-link-box{
  width:100%;background:var(--white);border:1px solid #e2e8f0;
  border-radius:10px;padding:10px 14px;position:relative;
}
.chain-link-box.chain-anchor{
  border:2px solid var(--navy);background:#f0f4ff;
}
.chain-link-addr{font-size:.82rem;font-weight:700;color:var(--txt)}
.chain-link-detail{font-size:.72rem;color:var(--txt-light);margin-top:2px}
.chain-link-status{
  display:inline-block;font-size:.62rem;font-weight:700;letter-spacing:.5px;
  text-transform:uppercase;padding:2px 8px;border-radius:4px;margin-top:4px;
}
.chain-link-status.chain-st-active{background:rgba(39,174,96,.1);color:var(--green)}
.chain-link-status.chain-st-problem{background:rgba(226,85,85,.1);color:var(--red)}
.chain-link-status.chain-st-complete{background:rgba(59,130,246,.1);color:var(--blue)}
.chain-link-status.chain-st-default{background:#f1f5f9;color:var(--txt-mid)}
.chain-connector{
  width:2px;height:18px;background:var(--navy);margin:0 auto;
}
.chain-pos-label{
  font-size:.6rem;text-transform:uppercase;letter-spacing:1.5px;
  color:var(--txt-light);font-weight:600;margin-bottom:6px;text-align:center;
}
</style>
</head>
<body>

{# ═══ PROPERTY CARD MACRO ═══════════════════════════════ #}
{% macro prop_card(p) %}
<div class="prop-card" id="card-{{ p.id }}">
  <div class="card-photo">
    {% if p.image_url %}<img class="card-photo-bg" src="{{ p.image_url|safe }}" alt="{{ p.address }}" style="background:{{ p.image_bg }}" onerror="this.style.display='none';this.nextElementSibling.style.display='block'"><div class="card-photo-bg" style="background:var(--navy-md);display:none"></div>{% else %}<div class="card-photo-bg" style="background:var(--navy-md)"></div>{% endif %}
    <span class="card-chip chip-{{ p.status }}">{{ p.status_label }}</span>
  </div>
  <div class="card-body">
    <div class="card-name">{{ p.address }}, {{ p.location }}</div>
    <div class="card-progress-row">
      <div class="ring-wrap">
        <svg viewBox="0 0 64 64">
          <circle class="ring-bg" cx="32" cy="32" r="27"/>
          <circle class="ring-fg clr-{{ p.status }}" cx="32" cy="32" r="27"
            stroke-dasharray="{{ (2 * 3.14159 * 27) | round(1) }}"
            stroke-dashoffset="{{ ((100 - p.progress) / 100 * 2 * 3.14159 * 27) | round(1) }}"/>
        </svg>
        <span class="ring-pct">{{ p.progress }}%</span>
      </div>
      <div class="card-duration">
        <div class="dur-label">Duration</div>
        <div class="dur-val">{{ p.duration_days }} days</div>
        <div class="dur-target">Target: {{ p.target_days }} days</div>
      </div>
    </div>
    <div class="card-checks">
      {% for c in p.card_checks %}
      <div class="chk {{ 'chk-done' if c.done else 'chk-pending' }}">
        <span class="chk-icon {{ 'done' if c.done else 'pending' }}">{% if c.done %}&#x2713;{% endif %}</span>
        {{ c.label }}
      </div>
      {% endfor %}
    </div>
  </div>
  {# ── Chain toggle ─────────────────────────────────── #}
  {% set cl = p.chain_links|default([]) %}
  <button class="chain-toggle" data-chain-id="{{ p.id }}" onclick="event.stopPropagation();toggleChain('{{ p.id }}')">
    <span class="chain-lbl">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>
      Chain {% if cl|length > 0 %}({{ cl|length }} link{{ 's' if cl|length != 1 }}){% else %}(no links added){% endif %}
    </span>
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
  </button>
  <div class="chain-panel" id="chainPanel-{{ p.id }}">
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
    <div class="hs" id="stat-at-risk"><div class="hs-val">{{ stats.at_risk }}</div><div class="hs-lbl">At Risk</div></div>
    <div class="hs" id="stat-action"><div class="hs-val">{{ stats.action }}</div><div class="hs-lbl">Action</div></div>
    <div class="hs" id="stat-exchanged"><div class="hs-val">{{ stats.exchanged }}</div><div class="hs-lbl">Exchanged</div></div>
    <div class="hs" id="stat-fee-pipeline"><div class="hs-val">&pound;{{ "{:,.0f}".format(stats.fee_pipeline) }}</div><div class="hs-lbl">Fee Pipeline</div></div>
    <div class="hs" id="stat-pipeline"><div class="hs-val">&pound;{{ "%.1f" | format(stats.property_pipeline / 1000000) }}M</div><div class="hs-lbl">Property Pipeline</div></div>
  </div>
</div>

<!-- ═══ PIPELINE FORECAST (clickable) ═══════════════════ -->
<div class="pipeline-section" id="pipelineSection">
  <div class="pipeline-header">
    <div>
      <div class="pipeline-title">&#x1F4CA; Pipeline Forecast</div>
      <div class="pipeline-sub">Click to view full analytics &bull; Manager access only</div>
    </div>
    <div class="ahead-badge">&#x26A1; 15% ahead of target</div>
  </div>
  <div class="pipeline-grid">
    <div class="pipe-card">
      <div class="pipe-period">This Week</div>
      <div class="pipe-count">{{ pipeline.this_week.count }}</div>
      <div class="pipe-value">&pound;{{ "%.1f" | format(pipeline.this_week.value / 1000000) }}M</div>
      <div class="pipe-confidence" style="color:var(--lime);font-weight:700">Fee: &pound;{{ "{:,.0f}".format(pipeline.this_week.fee) }}</div>
      <div class="pipe-bar"><div class="pipe-bar-fill" style="width:{{ pipeline.this_week.confidence }}%"></div></div>
      <div class="pipe-confidence">{{ pipeline.this_week.confidence }}% Confidence</div>
    </div>
    <div class="pipe-card">
      <div class="pipe-period">This Month</div>
      <div class="pipe-count">{{ pipeline.this_month.count }}</div>
      <div class="pipe-value">&pound;{{ "%.1f" | format(pipeline.this_month.value / 1000000) }}M</div>
      <div class="pipe-confidence" style="color:var(--lime);font-weight:700">Fee: &pound;{{ "{:,.0f}".format(pipeline.this_month.fee) }}</div>
      <div class="pipe-bar"><div class="pipe-bar-fill" style="width:{{ pipeline.this_month.confidence }}%"></div></div>
      <div class="pipe-confidence">{{ pipeline.this_month.confidence }}% Confidence</div>
    </div>
    <div class="pipe-card">
      <div class="pipe-period">This Quarter</div>
      <div class="pipe-count">{{ pipeline.this_quarter.count }}</div>
      <div class="pipe-value">&pound;{{ "%.1f" | format(pipeline.this_quarter.value / 1000000) }}M</div>
      <div class="pipe-confidence" style="color:var(--lime);font-weight:700">Fee: &pound;{{ "{:,.0f}".format(pipeline.this_quarter.fee) }}</div>
      <div class="pipe-bar"><div class="pipe-bar-fill" style="width:{{ pipeline.this_quarter.confidence }}%"></div></div>
      <div class="pipe-confidence">{{ pipeline.this_quarter.confidence }}% Confidence</div>
    </div>
  </div>
</div>

<!-- ═══ SEARCH BAR (sticky) ════════════════════════════════ -->
<div class="search-wrap" id="searchWrap">
  <div style="position:relative;max-width:640px;margin:0 auto">
    <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input class="search-input" id="searchInput" type="text" placeholder="Search by address, buyer or solicitor..." autocomplete="off">
  </div>
</div>

<!-- ═══ MAIN CONTENT — 4 SECTIONS ═══════════════════════ -->
<div class="content">
<div class="search-no-match" id="searchNoMatch">No properties found</div>

  {% for sec in sections %}
  <div id="section-{{ sec.id }}">
    <div class="section-banner {{ sec.border_class }}">
      <div class="section-banner-left">
        <h2>{{ sec.icon }} {{ sec.title }}</h2>
        <p>{{ sec.subtitle }}</p>
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
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
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
  {% endfor %}

</div>

<!-- ═══ PROPERTY MODAL ══════════════════════════════════ -->
<div class="modal-overlay" id="modalOverlay">
  <div class="modal" id="modalBox">
    <div class="m-hdr">
      <div>
        <h2 id="mAddr"></h2>
        <div class="m-loc" id="mLoc"></div>
      </div>
      <div style="display:flex;align-items:flex-start;gap:8px">
        <div class="m-price" id="mPrice"></div>
        <button class="m-close" id="mCloseBtn">&times;</button>
      </div>
    </div>

    <div class="m-prog">
      <div class="m-prog-bar"><div class="m-prog-fill" id="mProgFill"></div></div>
      <div class="m-prog-labels"><span>Offer Accepted</span><span id="mProgPct"></span><span>Completion</span></div>
    </div>

    <div class="m-body">
      <hr class="m-div">
      <div id="mAlertBox" class="m-alert" style="display:none">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span id="mAlertTxt"></span>
      </div>
      <div class="m-next">
        <div class="m-next-lbl">Next Action</div>
        <div class="m-next-txt" id="mNextAction"></div>
      </div>
      <div class="m-actions">
        <button class="m-btn m-btn-call" id="mBtnCall">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6A19.79 19.79 0 012.12 4.18 2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z"/></svg>
          <span id="mCallLbl">Call Buyer</span>
        </button>
        <button class="m-btn m-btn-done" id="mBtnDone">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          Mark Done
        </button>
        <button class="m-btn m-btn-outline" id="mBtnEmail">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
          Email
        </button>
      </div>
      <hr class="m-div">
      <div class="m-ms">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>
          Milestones
        </h3>
        <div class="ms-list" id="mMsList"></div>
      </div>
      <hr class="m-div">
      <div class="m-ms">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--txt-mid)" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          Notes &amp; Activity
        </h3>
        <div id="mActivityList"></div>
      </div>
      <hr class="m-div">
      <button class="m-det-toggle" id="mDetToggle">
        Full Details
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
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

<!-- ═══ ANALYTICS MODAL ═════════════════════════════════ -->
<div class="modal-overlay" id="analyticsOverlay">
  <div class="modal" style="max-width:700px">
    <div class="m-hdr">
      <div>
        <h2>Pipeline Analytics</h2>
        <div class="m-loc">Full analytics dashboard</div>
      </div>
      <button class="m-close" id="analyticsCloseBtn">&times;</button>
    </div>
    <div class="m-body" style="padding-bottom:20px">
      <hr class="m-div">
      <div class="analytics-chart">
        <div class="bar" style="height:30%"><span>Oct</span></div>
        <div class="bar" style="height:45%"><span>Nov</span></div>
        <div class="bar" style="height:60%"><span>Dec</span></div>
        <div class="bar" style="height:75%"><span>Jan</span></div>
        <div class="bar" style="height:95%;background:var(--lime);opacity:1"><span>Feb</span></div>
        <div class="bar" style="height:55%;opacity:.4"><span>Mar</span></div>
        <div class="bar" style="height:40%;opacity:.3"><span>Apr</span></div>
      </div>
      <div class="analytics-coming">Full analytics coming soon</div>
      <div class="analytics-rows">
        <div class="anal-row">
          <span class="anal-row-label">This Week</span>
          <span class="anal-row-value">5 completions &bull; &pound;1.2M</span>
        </div>
        <div class="anal-row">
          <span class="anal-row-label">This Month</span>
          <span class="anal-row-value">12 completions &bull; &pound;2.9M</span>
        </div>
        <div class="anal-row">
          <span class="anal-row-label">This Quarter</span>
          <span class="anal-row-value">28 completions &bull; &pound;6.8M</span>
        </div>
        <div class="anal-row">
          <span class="anal-row-label">Average Days to Completion</span>
          <span class="anal-row-value">14.2 days</span>
        </div>
        <div class="anal-row">
          <span class="anal-row-label">Target Performance</span>
          <span class="anal-row-value" style="color:var(--green);font-weight:700">15% ahead</span>
        </div>
      </div>
    </div>
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
  var mDetToggle = document.getElementById("mDetToggle");
  var mDetPanel  = document.getElementById("mDetPanel");
  var mDetGrid   = document.getElementById("mDetGrid");
  var mChain     = document.getElementById("mChain");

  function fmt(d){
    if(!d) return "\u2014";
    var dt=new Date(d);
    return dt.toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric"});
  }
  function patchProgression(progId,field,value,onSuccess){
    var body={};body[field]=value;
    fetch("/api/progression/"+progId,{
      method:"PATCH",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(body)
    }).then(function(r){return r.json();}).then(function(j){
      if(j.ok){if(onSuccess)onSuccess();}
      else{alert("Save failed: "+(j.error||"Unknown error"));}
    }).catch(function(e){alert("Network error: "+e.message);});
  }

  function price(n){ return "\u00a3"+n.toLocaleString(); }
  function fillCls(s){ return s==="stalled"?"clr-stalled":s==="at-risk"?"clr-at-risk":"clr-on-track"; }
  function alertCls(s){ return s==="stalled"?"m-alert-red":s==="at-risk"?"m-alert-amber":"m-alert-green"; }

  /* ── open modal ───────────────────────────────────── */
  function openModal(id){
    var p=null;
    for(var i=0;i<PROPS.length;i++){if(PROPS[i].id===id){p=PROPS[i];break;}}
    if(!p)return;
    currentProp=p;

    mAddr.textContent=p.address;
    mLoc.textContent=p.location;
    mPrice.textContent=price(p.price);

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

    var h="";
    for(var m=0;m<p.milestones.length;m++){
      var ms=p.milestones[m];
      var ic,tx,lc;
      if(ms.done===true){ic="ms-ic done";tx="\u2713";lc="ms-lb done-lb";}
      else if(ms.done===null){ic="ms-ic na";tx="N/A";lc="ms-lb";}
      else{ic="ms-ic pending";tx="";lc="ms-lb ms-pending-lb";}
      var dateStr=ms.date?' <span class="ms-date">'+fmt(ms.date)+'</span>':"";
      var editBtn=p._progression_id?'<button class="ms-edit-btn" data-field="'+ms.field+'" data-idx="'+m+'">Edit</button>':"";
      h+='<div class="ms-item" id="ms-row-'+m+'"><span class="'+ic+'">'+tx+'</span><span class="'+lc+'">'+ms.label+'</span>'+dateStr+editBtn+'</div>';
    }
    mMsList.innerHTML=h;

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
      ["Mortgage Offered",fmt(p.mortgage_offered)],["Survey Booked",fmt(p.survey_booked)],
      ["Survey Complete",fmt(p.survey_complete)],["Exchange Target",fmt(p.exchange_target)],
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
    if(e.key==="Escape"){closeModal();closeAnalytics();}
  };
  mDetToggle.onclick=function(){mDetPanel.classList.toggle("expanded");mDetToggle.classList.toggle("expanded");};
  mBtnCall.onclick=function(){if(currentProp)alert("Calling "+currentProp.buyer+" on "+currentProp.buyer_phone);};
  mBtnDone.onclick=function(){if(currentProp)alert("Marked done for "+currentProp.address+".\n\nAction: "+currentProp.next_action);};
  mBtnEmail.onclick=function(){if(currentProp)alert("Opening email for "+currentProp.address+" progression.");};

  /* ── CARD CLICK HANDLERS ──────────────────────────── */
  for(var i=0;i<PROPS.length;i++){
    (function(pid){
      var card=document.getElementById("card-"+pid);
      if(card){card.onclick=function(){openModal(pid);};}
    })(PROPS[i].id);
  }

  /* ── SHOW MORE TOGGLE HANDLERS ────────────────────── */
  var sectionIds=["needs-action","this-month","two-months","this-quarter","active-pipeline"];
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

  /* ── ANALYTICS MODAL ──────────────────────────────── */
  var analyticsOverlay=document.getElementById("analyticsOverlay");
  var analyticsCloseBtn=document.getElementById("analyticsCloseBtn");
  var pipelineSection=document.getElementById("pipelineSection");

  function closeAnalytics(){
    analyticsOverlay.classList.remove("open");
    document.body.style.overflow="";
  }

  pipelineSection.onclick=function(){
    analyticsOverlay.classList.add("open");
    document.body.style.overflow="hidden";
  };
  analyticsCloseBtn.onclick=function(e){e.stopPropagation();closeAnalytics();};
  analyticsOverlay.onclick=function(e){if(e.target===analyticsOverlay)closeAnalytics();};

  /* ── STATS BAR — scroll to sections ───────────────── */
  var statMap={
    "stat-active":"section-active-pipeline",
    "stat-on-track":"section-this-month",
    "stat-at-risk":"section-needs-action",
    "stat-action":"section-needs-action",
    "stat-exchanged":"section-this-month",
    "stat-fee-pipeline":"section-active-pipeline",
    "stat-pipeline":"section-active-pipeline"
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
  var allSections=document.querySelectorAll(".content > div[id^='section-']");
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

})();
</script>
</body>
</html>"""



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


def _build_live_dashboard_data():
    """Query Supabase and build PROPERTIES, SECTIONS, PIPELINE, STATS for the dashboard.

    Starts from sales_pipeline (source of truth) and joins sales_progression
    for milestone/status detail. Only properties in sales_pipeline appear.
    """
    from datetime import date as _date

    # Import inside function to avoid circular import at module load.
    from routes.crm import FALLBACK_GRADIENTS, STATUS_LABELS, STATUS_MAP
    from routes.crm import _card_checks_from_record, _milestones_from_record, _progress_from_record

    # 1. Fetch all four tables
    pipe_rows = fetch_sales_pipeline()
    prog_rows = fetch_sales_progression()  # all rows, no status filter
    img_rows = fetch_property_images()
    chain_rows = fetch_chain_links()

    # 1b. Build image lookup — keyed by alto ref AND normalized address
    #     Also build property-id lookup for chain_links resolution
    _img_by_ref = {}
    _img_by_addr = {}
    _propid_by_ref = {}
    _propid_by_addr = {}
    for row in img_rows:
        prop_id = row.get("id")
        ref = (row.get("ref") or "").strip()
        addr = _normalize_addr(row.get("address") or "")
        if ref and prop_id:
            _propid_by_ref[ref] = prop_id
        if addr and prop_id:
            _propid_by_addr[addr] = prop_id
        # Resolve best URL: image_url first, then photo_urls[1] (skip index 0)
        url = (row.get("image_url") or "").strip() or None
        if not url:
            urls = row.get("photo_urls") or []
            if isinstance(urls, list) and len(urls) > 1:
                url = (urls[1] or "").strip() or None
        if not url:
            continue
        if ref:
            _img_by_ref[ref] = url
        if addr:
            _img_by_addr[addr] = url

    # 1c. Build chain_links lookup by property_id
    _chain_by_propid = {}
    for cl in chain_rows:
        pid = cl.get("property_id")
        if pid:
            _chain_by_propid.setdefault(pid, []).append(cl)
    # Sort each list: above links first, then below
    _pos_order = {"above": 0, "below": 1}
    for pid in _chain_by_propid:
        _chain_by_propid[pid].sort(key=lambda x: _pos_order.get(x.get("chain_position", ""), 2))

    def _resolve_image(pipe_row):
        """Find the best image URL for a pipeline property."""
        ref = (pipe_row.get("alto_ref") or "").strip()
        if ref and ref in _img_by_ref:
            return _img_by_ref[ref]
        addr = _normalize_addr(pipe_row.get("property_address") or "")
        return _img_by_addr.get(addr, "")

    def _resolve_property_id(pipe_row):
        """Find the properties.id for a pipeline property (for chain_links lookup)."""
        ref = (pipe_row.get("alto_ref") or "").strip()
        if ref and ref in _propid_by_ref:
            return _propid_by_ref[ref]
        addr = _normalize_addr(pipe_row.get("property_address") or "")
        return _propid_by_addr.get(addr)

    # 2. Build progression lookup by normalized address
    prog_lookup = {}
    for pr in prog_rows:
        key = _normalize_addr(pr.get("property_address", ""))
        prog_lookup[key] = pr
    prog_norm_keys = list(prog_lookup.keys())

    today = _date.today()

    # Map pipeline status strings to progression-style statuses
    PIPE_STATUS_MAP = {
        "Under Offer (SSTC)": "active",
        "Under Offer": "active",
        "Exchanged": "exchanged",
    }

    # 3. Build property list — iterate over pipeline, join progression
    properties = []
    for i, pipe in enumerate(pipe_rows):
        addr = pipe.get("property_address", "")

        # Find matching progression row
        prog = _match_pipeline(addr, prog_lookup, prog_norm_keys)

        # Status: from pipeline only
        raw_status = PIPE_STATUS_MAP.get(pipe.get("status", ""), "active")

        # Price from pipeline.current_price
        price = float(pipe.get("current_price") or 0)

        # Duration = today - pipeline.date_agreed
        duration = 0
        date_agreed_str = pipe.get("date_agreed")
        if date_agreed_str:
            try:
                agreed = datetime.strptime(str(date_agreed_str), "%Y-%m-%d").date()
                duration = (today - agreed).days
            except Exception:
                pass

        # est_completion from pipeline
        est_comp_str = pipe.get("est_completion")
        est_comp_date = None
        if est_comp_str:
            try:
                est_comp_date = datetime.strptime(str(est_comp_str), "%Y-%m-%d").date()
            except Exception:
                pass

        status = STATUS_MAP.get(raw_status, "on-track")
        progress = _progress_from_record(prog) if prog else 10
        prop_id = str(prog.get("id", f"prop-{i}")) if prog else f"pipe-{i}"

        # Use progression fields where available, fall back to pipeline
        r = prog or {}

        properties.append(
            {
                "id": prop_id,
                "address": addr or "Unknown",
                "location": (r.get("branch") or "").title() or "Eden Valley",
                "price": price,
                "status": status,
                "status_label": STATUS_LABELS.get(status, "ON TRACK"),
                "progress": progress,
                "duration_days": duration,
                "target_days": 60,
                "days_since_update": 0,
                "card_checks": _card_checks_from_record(r),
                "milestones": _milestones_from_record(r),
                "buyer": r.get("buyer_name") or "\u2014",
                "buyer_phone": r.get("buyer_phone") or "\u2014",
                "buyer_solicitor": r.get("buyer_solicitor") or pipe.get("buyers_solicitor") or "\u2014",
                "buyer_sol_phone": "\u2014",
                "seller_solicitor": r.get("vendor_solicitor") or pipe.get("vendors_solicitor") or "\u2014",
                "seller_sol_phone": "\u2014",
                "offer_date": r.get("offer_accepted"),
                "memo_sent": r.get("memo_sent"),
                "searches_ordered": r.get("searches_ordered"),
                "searches_received": r.get("searches_received"),
                "enquiries_raised": r.get("enquiries_raised"),
                "enquiries_answered": r.get("enquiries_answered"),
                "mortgage_offered": r.get("mortgage_offered"),
                "survey_booked": r.get("survey_booked"),
                "survey_complete": r.get("survey_complete"),
                "exchange_target": r.get("exchange_date"),
                "completion_target": r.get("completion_date"),
                "chain": "\u2014",
                "alert": r.get("notes") if raw_status == "problem" else None,
                "next_action": r.get("notes") or "\u2014",
                "image_bg": FALLBACK_GRADIENTS[i % len(FALLBACK_GRADIENTS)],
                "image_url": _resolve_image(pipe),
                "chain_links": _chain_by_propid.get(_resolve_property_id(pipe) or "", []),
                "activity": [],
                # Notes for modal display
                "notes": r.get("notes") or "",
                "nuvu_notes": r.get("nuvu_notes") or "",
                "buyer_solicitor_notes": r.get("buyer_solicitor_notes") or "",
                "seller_solicitor_notes": r.get("seller_solicitor_notes") or "",
                # Internal fields
                "_progression_id": r.get("id"),
                "_raw_status": raw_status,
                "_fee": r.get("fee"),
                "_pipe_fee": float(pipe.get("fee") or 0),
                "_staff_initials": r.get("staff_initials") or pipe.get("negotiator") or "\u2014",
                "_est_comp_date": est_comp_date.isoformat() if est_comp_date else None,
                "_date_agreed": str(date_agreed_str) if date_agreed_str else None,
                "_mortgage_broker": r.get("mortgage_broker") or "\u2014",
                "_surveyor": r.get("surveyor") or "\u2014",
                "_buyer_email": r.get("buyer_email") or "\u2014",
                "_vendor_name": r.get("vendor_name") or "\u2014",
                "_vendor_phone": r.get("vendor_phone") or "\u2014",
                "_vendor_email": r.get("vendor_email") or "\u2014",
                "_sewage_type": r.get("sewage_type") or "\u2014",
                "_invoice_status": r.get("invoice_status") or "\u2014",
                "_nuvu_notes": r.get("nuvu_notes") or "\u2014",
                "_property_type": r.get("property_type") or "\u2014",
                "_beds": r.get("beds"),
                "_baths": r.get("baths"),
            }
        )

    # 4. Classify into sections
    needs_action = []
    sec_this_month = []
    sec_two_months = []
    sec_this_quarter = []
    sec_active_pipeline = []
    exchanged_count = 0

    for p in properties:
        raw = p["_raw_status"]

        # Exchanged: count only, not shown in sections
        if raw == "exchanged":
            exchanged_count += 1
            continue

        est = p.get("_est_comp_date")
        est_date = datetime.strptime(est, "%Y-%m-%d").date() if est else None
        days_to_comp = (est_date - today).days if est_date else None

        # Needs Action check
        is_needs_action = False
        if raw in ("problem", "incomplete_chain"):
            is_needs_action = True
        elif raw == "active" and p.get("offer_date") and not p.get("memo_sent"):
            if p.get("_date_agreed"):
                try:
                    agreed = datetime.strptime(p["_date_agreed"], "%Y-%m-%d").date()
                    if (today - agreed).days > 7:
                        is_needs_action = True
                except Exception:
                    pass

        if is_needs_action:
            needs_action.append(p)
        elif raw in ("active", "development") and days_to_comp is not None and days_to_comp <= 30:
            sec_this_month.append(p)
        elif raw in ("active", "development") and days_to_comp is not None and days_to_comp <= 60:
            sec_two_months.append(p)
        elif raw in ("active", "development") and days_to_comp is not None and days_to_comp <= 90:
            sec_this_quarter.append(p)
        else:
            sec_active_pipeline.append(p)

    # 5. Build section dicts
    def _make_section(sid, icon, title, subtitle, border, items):
        visible = items[:3]
        hidden = items[3:]
        avg = int(sum(p["progress"] for p in items) / len(items)) if items else 0
        color = "#e25555" if border == "stalled-banner" else "#e88a3a" if border == "amber-banner" else "#27ae60"
        return {
            "id": sid,
            "icon": icon,
            "title": title,
            "subtitle": subtitle,
            "avg_progress": avg,
            "avg_color": color,
            "border_class": border,
            "visible_ids": [],
            "hidden_ids": [],
            "visible": visible,
            "hidden": hidden,
            "extra_count": 0,
        }

    sections = []
    if needs_action:
        sections.append(
            _make_section(
                "needs-action",
                "\U0001F6A8",
                "Needs Action",
                f"{len(needs_action)} transactions requiring attention",
                "stalled-banner",
                needs_action,
            )
        )
    if sec_this_month:
        sections.append(
            _make_section(
                "this-month",
                "\U0001F4C5",
                "This Month",
                f"{len(sec_this_month)} completing within 30 days",
                "green-banner",
                sec_this_month,
            )
        )
    if sec_two_months:
        sections.append(
            _make_section(
                "two-months",
                "\U0001F4CA",
                "Two Months",
                f"{len(sec_two_months)} completing in 31\u201360 days",
                "blue-banner",
                sec_two_months,
            )
        )
    if sec_this_quarter:
        sections.append(
            _make_section(
                "this-quarter",
                "\U0001F4C8",
                "This Quarter",
                f"{len(sec_this_quarter)} completing in 61\u201390 days",
                "amber-banner",
                sec_this_quarter,
            )
        )
    if sec_active_pipeline:
        sections.append(
            _make_section(
                "active-pipeline",
                "\U0001F3E0",
                "Active Pipeline",
                f"{len(sec_active_pipeline)} active transactions",
                "blue-banner",
                sec_active_pipeline,
            )
        )

    # 6. Stats
    active_props = [p for p in properties if p["_raw_status"] == "active"]
    active_count = len(active_props)
    on_track_count = sum(
        1
        for p in active_props
        if p.get("_est_comp_date")
        and (datetime.strptime(p["_est_comp_date"], "%Y-%m-%d").date() - today).days > 30
    )
    at_risk_count = sum(1 for p in properties if p["_raw_status"] == "problem")
    action_count = len(needs_action)
    # All non-completed, non-exchanged properties for pipeline totals
    pipeline_props = [p for p in properties if p["_raw_status"] not in ("exchanged",)]
    property_pipeline = sum(p["price"] for p in pipeline_props if p["price"])
    fee_pipeline = sum(p["_pipe_fee"] for p in pipeline_props if p["_pipe_fee"])

    stats = {
        "active": active_count,
        "on_track": on_track_count,
        "at_risk": at_risk_count,
        "action": action_count,
        "exchanged": exchanged_count,
        "fee_pipeline": fee_pipeline,
        "property_pipeline": property_pipeline,
    }

    # 7. Pipeline forecast (using section counts)
    pipeline = {
        "this_week": {
            "count": len(sec_this_month),
            "value": sum(p["price"] for p in sec_this_month),
            "fee": sum(p["_pipe_fee"] for p in sec_this_month),
            "confidence": 90,
        },
        "this_month": {
            "count": len(sec_two_months),
            "value": sum(p["price"] for p in sec_two_months),
            "fee": sum(p["_pipe_fee"] for p in sec_two_months),
            "confidence": 75,
        },
        "this_quarter": {
            "count": len(sec_this_quarter) + len(sec_active_pipeline),
            "value": property_pipeline,
            "fee": fee_pipeline,
            "confidence": 60,
        },
    }

    return properties, sections, stats, pipeline


@dashboard_bp.route("/")
def dashboard():
    try:
        properties, sections, stats, pipeline = _build_live_dashboard_data()
    except Exception as e:
        # Fallback: show error
        return f"<h2>Error loading live data</h2><pre>{e}</pre>", 500

    return render_template_string(
        DASHBOARD_HTML,
        sections=sections,
        stats=stats,
        pipeline=pipeline,
        properties_json=json.dumps(properties, default=str),
    )

