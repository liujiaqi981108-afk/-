/**
 * 9-Agent AI Short-Film Pre-Production & Storyboard Studio Frontend Controller
 */

const AGENT_DEFS = [
  { id: "agent_01_director", code: "01", label: "总导演统筹" },
  { id: "agent_02_story", code: "02", label: "剧作策划总监" },
  { id: "agent_03_storyboard", code: "03", label: "帧级分镜导演" },
  { id: "agent_04_art", code: "04", label: "三视图场景总监" },
  { id: "agent_05_t2i", code: "05", label: "防穿模生图师" },
  { id: "agent_06_critic", code: "06", label: "作画监督质检" },
  { id: "agent_07_motion", code: "07", label: "动态物理运镜" },
  { id: "agent_08_voice", code: "08", label: "角色声线声景" },
  { id: "agent_09_editor", code: "09", label: "影视剪辑调色" },
];

const state = {
  currentProjectId: null,
  project: null,
  activeTab: "tab-dramaturgy",
  sse: null,
  busyAction: false,
};

function esc(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(errText || `HTTP ${res.status}`);
  }
  return res.json();
}

/* ============================================================================
   9-Agent Top Pipeline Rail & Gate Banner
   ============================================================================ */

function getCompletedAgentCodes(stage) {
  switch (stage) {
    case "CREATED":
    case "PLANNING_SCRIPT":
      return new Set();
    case "AWAITING_SCRIPT_APPROVAL":
      return new Set(["01", "02", "03"]);
    case "BUILDING_ASSETS":
      return new Set(["01", "02", "03"]);
    case "AWAITING_ASSET_APPROVAL":
      return new Set(["01", "02", "03", "04", "08"]);
    case "GENERATING_STORYBOARD":
    case "REVIEWING_STORYBOARD":
      return new Set(["01", "02", "03", "04", "08"]);
    case "AWAITING_STORYBOARD_APPROVAL":
      return new Set(["01", "02", "03", "04", "05", "06", "08"]);
    case "COMPILING_MANIFEST":
      return new Set(["01", "02", "03", "04", "05", "06", "08"]);
    case "PHASE1_COMPLETED":
    case "GENERATING_VIDEOS":
    case "COMPOSITING_FINAL":
    case "COMPLETED":
      return new Set(["01", "02", "03", "04", "05", "06", "07", "08", "09"]);
    default:
      return new Set();
  }
}

function renderAgentRail() {
  const rail = document.getElementById("agent-pipeline-rail");
  const stg = state.project ? state.project.stage : "IDLE";
  const activeId = state.project ? state.project.active_agent : null;
  const doneSet = getCompletedAgentCodes(stg);

  rail.innerHTML = AGENT_DEFS.map((ag) => {
    const isDone = doneSet.has(ag.code);
    const isActive =
      activeId === ag.id &&
      ![
        "AWAITING_SCRIPT_APPROVAL",
        "AWAITING_ASSET_APPROVAL",
        "AWAITING_STORYBOARD_APPROVAL",
        "PHASE1_COMPLETED",
        "COMPLETED",
      ].includes(stg);
    const cls = isActive ? "agent-node active" : isDone ? "agent-node done" : "agent-node";
    return `
      <div class="${cls}" title="${esc(ag.code + " " + ag.label)}">
        <span class="agent-code">${esc(ag.code)}</span>
        <span class="agent-label">${esc(ag.label)}</span>
      </div>
    `;
  }).join("");

  document.getElementById("stage-pill").textContent = stg;
  const exportBtn = document.getElementById("btn-export-manifest");
  if (state.project && state.project.manifest_url) {
    exportBtn.style.display = "inline-flex";
  } else {
    exportBtn.style.display = "none";
  }
}

function renderGateBanner() {
  const banner = document.getElementById("hitl-gate-banner");
  const titleEl = document.getElementById("gate-banner-title");
  const descEl = document.getElementById("gate-banner-desc");
  const btnEl = document.getElementById("btn-gate-approve");

  if (!state.project) {
    banner.style.display = "none";
    return;
  }

  const stg = state.project.stage;
  banner.className = "gate-banner";
  btnEl.disabled = state.busyAction;

  if (stg === "AWAITING_SCRIPT_APPROVAL") {
    banner.style.display = "flex";
    titleEl.textContent = "关卡 1 待审：总导演色彩总谱、高概念剧作策划与 24fps 帧级 6W1H 分镜台本已生成";
    descEl.textContent = "可在「01/02」标签页审阅或在线修改单镜台词、时长、朝向与单/双关键帧策略；确认后将启动 1440x960 角色正侧背三视图、场景母版与声学基因建档。";
    btnEl.textContent = "通过关卡 1 · 启动三视图与声学资产建档 →";
    btnEl.style.display = "inline-flex";
    btnEl.onclick = () => triggerGateAction("approve-script", "tab-characters");
  } else if (stg === "AWAITING_ASSET_APPROVAL") {
    banner.style.display = "flex";
    titleEl.textContent = "关卡 2 待审：1440x960 正/侧/背角色三视图、契诃夫随身物双态卡、五维声学卡与罗盘空镜母版已生成";
    descEl.textContent = "可在「03/04」标签页点击大图检视或输入修改备注单独重抽三视图/母版；锁定后将作为一致性参考垫图驱动全片防穿模分镜生图。";
    btnEl.textContent = "通过关卡 2 · 锁定资产并生成全片防穿模关键帧 →";
    btnEl.style.display = "inline-flex";
    btnEl.onclick = () => triggerGateAction("approve-assets", "tab-keyframes");
  } else if (stg === "AWAITING_STORYBOARD_APPROVAL") {
    banner.style.display = "flex";
    titleEl.textContent = "关卡 3 待审：全片单/双关键帧分镜图、作画监督三图交叉质检与连环画拼条连续性核验已全部通过";
    descEl.textContent = "可在「05」画板查看首尾双关键帧、双人左右分仓防串色与二级转角避障自愈记录（支持任意单镜微调重抽），确认后编译 Phase 2 总单。";
    btnEl.textContent = "通过关卡 3 · 编译动态物理运镜与声画剪辑总单 →";
    btnEl.style.display = "inline-flex";
    btnEl.onclick = () => triggerGateAction("approve-storyboard", "tab-post-manifest");
  } else if (stg === "PHASE1_COMPLETED") {
    banner.style.display = "flex";
    banner.classList.add("completed");
    titleEl.textContent = "✓ Phase 1 视听工程与分镜已就绪 — 可直接启动 Phase 2 真视频生成与成片剪辑！";
    descEl.textContent = state.project.error_message
      ? `⚠️ 上次中断提示：${state.project.error_message}`
      : "支持调用本地 Chrome 挂载的 Google Flow 自动生成首尾帧动态视频（或在 07 放映室逐镜生成 / 手动上传 .mp4），并自动合成神经配音、四轨拟音与安全区字幕母带。";
    btnEl.textContent = "🎬 启动 Phase 2 真视频渲染与母带合片 →";
    btnEl.style.display = "inline-flex";
    btnEl.onclick = () => triggerGateAction("run-phase2", "tab-screening-room");
  } else if (stg === "COMPLETED") {
    banner.style.display = "flex";
    banner.classList.add("completed");
    titleEl.textContent = "🎉 全片 H.264 + 44.1kHz 立体声母带成片 (final_master.mp4) 压制完成！";
    descEl.textContent = "已完成手术刀黄金帧裁剪、高潮曲线变速、四轨神经配音拟音混音及底部安全区字幕合成。";
    btnEl.textContent = "▶ 前往 07 成片放映室观看 / 下载 →";
    btnEl.style.display = "inline-flex";
    btnEl.onclick = () => setActiveTab("tab-screening-room");
  } else {
    banner.style.display = "flex";
    titleEl.textContent = `9-Agent 片场正在协同执行中 (${stg})…`;
    descEl.textContent = "请关注右侧实时 SSE 监修日志流，工作流将在下一关卡自动呈现最新成果。";
    btnEl.style.display = "none";
  }
}

async function triggerGateAction(endpointSuffix, switchTabAfter) {
  if (!state.currentProjectId || state.busyAction) return;
  state.busyAction = true;
  renderGateBanner();
  try {
    await apiFetch(`/api/projects/${state.currentProjectId}/${endpointSuffix}?background=true`, {
      method: "POST",
    });
    if (switchTabAfter) {
      setActiveTab(switchTabAfter);
    }
    await refreshCurrentProject();
  } catch (err) {
    alert(`推进关卡失败: ${err.message}`);
  } finally {
    state.busyAction = false;
    renderGateBanner();
  }
}

/* ============================================================================
   7 Specialized Studio Workbenches Rendering
   ============================================================================ */

function renderWorkbench() {
  const container = document.getElementById("workbench-content");
  if (!state.project) return;

  const p = state.project;
  if (state.activeTab === "tab-dramaturgy") {
    container.innerHTML = renderTabDramaturgy(p);
  } else if (state.activeTab === "tab-storyboard-script") {
    container.innerHTML = renderTabStoryboardScript(p);
    bindScriptEditHandlers();
  } else if (state.activeTab === "tab-characters") {
    container.innerHTML = renderTabCharacters(p);
    bindCharacterHandlers();
  } else if (state.activeTab === "tab-scenes") {
    container.innerHTML = renderTabScenes(p);
    bindSceneHandlers();
  } else if (state.activeTab === "tab-keyframes") {
    container.innerHTML = renderTabKeyframes(p);
    bindKeyframeHandlers();
  } else if (state.activeTab === "tab-post-manifest") {
    container.innerHTML = renderTabPostManifest(p);
  } else if (state.activeTab === "tab-screening-room") {
    container.innerHTML = renderTabScreeningRoom(p);
    bindScreeningRoomHandlers();
  }

  bindLightboxTriggers(container);
}

function renderTabDramaturgy(p) {
  const ch = p.director_charter;
  const st = p.story_strategy;
  if (!ch || !st) {
    return `<div class="section-card">01 总导演与 02 剧作策划总监正在立项推演中，请稍候…</div>`;
  }

  const colorNodesHtml = (ch.color_script_arc || [])
    .map((node) => {
      const segs = (node.dominant_and_accent_hex || [])
        .map((hx) => `<span class="swatch-seg" style="background:${esc(hx)};" title="${esc(hx)}"></span>`)
        .join("");
      return `
        <div class="color-act-box">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <strong style="text-transform:uppercase;font-size:12px;">${esc(node.act_phase)}</strong>
            <span class="pill">${esc(node.luminance_contrast_ratio)}</span>
          </div>
          <div class="swatch-bar">${segs}</div>
          <div style="font-size:12px;color:var(--accent-amber);font-weight:600;">${esc(node.kelvin_temp)}</div>
          <div style="font-size:11.5px;color:var(--text-secondary);margin-top:3px;">${esc(node.lighting_mood_note)}</div>
        </div>
      `;
    })
    .join("");

  const arbHtml = (ch.arbitration_logs || [])
    .map((l) => `<div style="font-size:12.5px;padding:6px 10px;background:var(--bg-surface-2);border-radius:4px;margin-bottom:6px;">${esc(l)}</div>`)
    .join("");

  const charsHtml = (st.iceberg_characters || [])
    .map(
      (c) => `
      <div class="kv-box">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
          <strong>${esc(c.name)}</strong>
          <span class="pill pill-amber">${esc(c.archetype_and_role)}</span>
        </div>
        <div style="font-size:12.5px;margin-bottom:4px;"><span style="color:var(--text-secondary);">外在克制伪装 (Mask)：</span>${esc(c.outer_mask)}</div>
        <div style="font-size:12.5px;margin-bottom:4px;"><span style="color:var(--accent-amber);">冰山下潜流 (Hidden Agenda)：</span>${esc(c.hidden_agenda)}</div>
        <div style="font-size:12.5px;margin-bottom:4px;"><span style="color:#52d1c2;">标志性微习惯 (Tic)：</span>${esc(c.behavioral_tic)}</div>
        <div style="font-size:12px;color:var(--text-secondary);">人物微弧变：${esc(c.micro_arc_shift)}</div>
      </div>
    `
    )
    .join("");

  const chekhovHtml = (st.chekhov_props || [])
    .map(
      (cp) => `
      <div class="kv-grid" style="margin-top:8px;">
        <div class="kv-box"><div class="kv-label">第一幕 · 前埋 (PLANT · ${esc(cp.prop_name)})</div><div class="kv-val">${esc(cp.plant_beat)}</div></div>
        <div class="kv-box"><div class="kv-label">中段 · 异变蓄势 (ESCALATION)</div><div class="kv-val">${esc(cp.escalation_beat)}</div></div>
        <div class="kv-box"><div class="kv-label">高潮 · 引爆回收 (PAYOFF)</div><div class="kv-val">${esc(cp.payoff_climax_beat)}</div></div>
      </div>
    `
    )
    .join("");

  const subtextRows = (st.subtext_dialogue_list || [])
    .map(
      (ln) => `
      <tr>
        <td>Beat ${ln.beat_index}</td>
        <td><strong>${esc(ln.speaker_name)}</strong></td>
        <td style="color:var(--accent-amber);font-weight:600;">「${esc(ln.surface_line)}」</td>
        <td>${esc(ln.subtext_intent)}</td>
        <td style="font-family:var(--font-mono);">${ln.silence_before_ms}ms</td>
      </tr>
    `
    )
    .join("");

  const ledgerRows = (ch.continuity_ledger || [])
    .map(
      (le) => `
      <tr>
        <td style="font-family:var(--font-mono);">S${String(le.shot_id).padStart(2, "0")}</td>
        <td>${esc(Object.values(le.character_physical_states || {}).join(" | "))}</td>
        <td>${esc(Object.values(le.prop_spatial_states || {}).join(" | "))}</td>
        <td>${esc((le.environment_damage_persisted || []).join("；") || "初始完好")}</td>
      </tr>
    `
    )
    .join("");

  return `
    <section class="section-card">
      <div class="section-card-header">
        <h3 class="section-card-title">01 总导演美学宪章 &amp; 五幕色彩情绪总谱 · ${esc(ch.title)}</h3>
        <span class="pill pill-amber">${esc(p.aspect_ratio)} 构图戒律已生效</span>
      </div>
      <div class="kv-grid" style="margin-bottom:14px;">
        <div class="kv-box"><div class="kv-label">全局唯一视觉介质基因锁</div><div class="kv-val">${esc(ch.visual_medium_lock)}</div></div>
        <div class="kv-box"><div class="kv-label">画幅纵向调度与底部20%净空戒律</div><div class="kv-val">${esc(ch.aspect_framing_mandate)}</div></div>
      </div>
      <div class="color-script-grid">${colorNodesHtml}</div>
      <div style="margin-top:12px;">${arbHtml}</div>
    </section>

    <section class="section-card">
      <div class="section-card-header">
        <h3 class="section-card-title">02 高级剧作策划总监：高概念反差、信息差悬念链 &amp; 冰山人物</h3>
        <span class="pill pill-teal">${st.anti_cliche_audit_passed ? "✓ 反AI套话洁癖审查通过" : "待精修"}</span>
      </div>
      <div class="kv-grid" style="margin-bottom:14px;">
        <div class="kv-box"><div class="kv-label">一句话高概念认知反差 (High-Concept Irony)</div><div class="kv-val">${esc(st.high_concept_irony)}</div></div>
        <div class="kv-box"><div class="kv-label">唯一核心情绪货币 &amp; 信息差模型</div><div class="kv-val">${esc(st.single_emotional_currency)} <span class="pill">${esc(st.asymmetry_mode)}</span></div></div>
        <div class="kv-box"><div class="kv-label">开篇 0.8s 划屏阻断钩子</div><div class="kv-val">${esc(st.opening_0_8s_hook_design)}</div></div>
      </div>
      <div class="kv-label" style="margin-bottom:6px;">每 3–5 秒微钩子接力链 (Micro-Hook Relay)</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px;margin-bottom:16px;">
        ${(st.micro_hook_relay_chain || []).map((h) => `<div class="kv-box" style="font-size:12.5px;">${esc(h)}</div>`).join("")}
      </div>
      <div class="kv-label" style="margin-bottom:6px;">冰山人物塑造 (外在克制伪装 vs 内在真实潜流)</div>
      <div class="kv-grid" style="margin-bottom:16px;">${charsHtml}</div>

      <div class="kv-label">契诃夫之枪 · 随身信物三幕伏笔回收链 (强绑定下游三视图与帧拟音)</div>
      ${chekhovHtml}

      <div class="kv-label" style="margin:16px 0 8px 0;">指东打西潜台词对白表 (单句 &lt;= 11字惜字铁律)</div>
      <table class="data-table">
        <thead><tr><th>节拍</th><th>说话人</th><th>字面惜字台词</th><th>弦外之音潜台词真意</th><th>开口前留白</th></tr></thead>
        <tbody>${subtextRows}</tbody>
      </table>

      <div class="kv-grid" style="margin-top:14px;">
        <div class="kv-box"><div class="kv-label">暴风雨前的死寂 (Silence Before Impact)</div><div class="kv-val">${esc(st.quiet_before_storm_beat)}</div></div>
        <div class="kv-box"><div class="kv-label">高复播首尾闭环 &amp; 评论区列文虎克彩蛋</div><div class="kv-val">${esc(st.loop_and_easter_egg)}</div></div>
      </div>
    </section>

    <section class="section-card">
      <div class="section-card-header">
        <h3 class="section-card-title">01 场记级跨镜头连续性状态总账本 (Master Continuity Ledger)</h3>
        <span class="pill">严防衣着自动复原与道具瞬移</span>
      </div>
      <table class="data-table">
        <thead><tr><th>镜号</th><th>人物衣着/干湿/战损不可逆继承</th><th>随身道具空间位置守恒</th><th>场景交互痕迹持续保留</th></tr></thead>
        <tbody>${ledgerRows}</tbody>
      </table>
    </section>
  `;
}

function renderTabStoryboardScript(p) {
  const shots = p.shots || [];
  if (!shots.length) {
    return `<div class="section-card">03 视听分镜与帧级调度导演正在拆解分镜中…</div>`;
  }

  const totalSec = shots.reduce((acc, s) => acc + s.duration_budget.final_duration_sec, 0);
  const segsHtml = shots
    .map((s) => {
      const pct = Math.max(8, (s.duration_budget.final_duration_sec / totalSec) * 100);
      return `
        <div class="pacing-seg ${esc(s.beat_phase)}" style="width:${pct.toFixed(1)}%;" title="${esc(s.duration_budget.duration_rationale)}">
          <strong>S${String(s.shot_id).padStart(2, "0")} · ${s.duration_budget.final_duration_sec}s</strong>
          <span style="color:var(--text-secondary);font-size:10px;">${esc(s.six_w_one_h.which_shot_size)} · ${s.duration_budget.total_frames_24fps}f</span>
        </div>
      `;
    })
    .join("");

  const cardsHtml = shots
    .map((s) => {
      const m = s.six_w_one_h;
      const mid = (s.mid_beat_frames || [])[0] || {};
      const dualBadge =
        m.which_keyframe_strategy === "first_and_last_frames"
          ? `<span class="pill pill-crimson">首尾双关键帧锁死 (Frame 01 + Frame ${s.end_frame.frame_index})</span>`
          : `<span class="pill">单首帧定格 (Frame 01)</span>`;

      return `
        <section class="section-card">
          <div class="section-card-header">
            <div>
              <strong style="font-size:15px;">SHOT ${String(s.shot_id).padStart(2, "0")}</strong>
              <span class="pill pill-amber" style="margin-left:6px;">${esc(s.beat_phase.toUpperCase())}</span>
              <span class="pill" style="margin-left:4px;">${m.timeline_in_sec}s → ${m.timeline_out_sec}s (${s.duration_budget.final_duration_sec}s / ${s.duration_budget.total_frames_24fps}帧)</span>
            </div>
            <div>${dualBadge}</div>
          </div>

          <div style="font-size:12px;color:var(--accent-amber);margin-bottom:10px;font-family:var(--font-mono);">
            ⏱ ${esc(s.duration_budget.duration_rationale)} | I2V裁剪窗: Frame ${s.duration_budget.trim_in_frame}–${s.duration_budget.trim_out_frame}
          </div>

          <div class="kv-grid">
            <div class="kv-box"><div class="kv-label">WHO · 主次人物与连续状态</div><div class="kv-val">主焦点: <code>${esc(m.primary_subject_id)}</code> (${esc(m.co_present_character_ids.join(", "))})<br/>${esc(m.secondary_and_offscreen_who)}</div></div>
            <div class="kv-box"><div class="kv-label">WHAT · 唯一叙事事件与环境连锁反馈</div><div class="kv-val">${esc(m.physical_action_and_prop_event)}<br/><span style="color:var(--text-secondary);">环境反馈：${esc(m.environmental_chain_reaction)}</span></div></div>
            <div class="kv-box"><div class="kv-label">WHERE &amp; WHEN · 罗盘朝向与空间接地</div><div class="kv-val">机位朝向场景 <strong>${esc(m.camera_compass_facing.toUpperCase())}</strong> 墙 | ${esc(m.spatial_zone_and_ground)} | 流速: <code>${esc(m.temporal_speed_mode)}</code></div></div>
            <div class="kv-box"><div class="kv-label">WHICH · 焦段景深、拉焦与切点抉择</div><div class="kv-val">${esc(m.which_shot_size)} · ${esc(m.which_lens_and_aperture)} | 切点: <code>${esc(m.which_cut_transition)}</code><br/>跟焦: ${esc(m.which_focus_plane_and_shift)}</div></div>
            <div class="kv-box"><div class="kv-label">WHY · 戏剧动机与留存钩子</div><div class="kv-val">${esc(m.dramatic_motivation)}</div></div>
            <div class="kv-box"><div class="kv-label">HOW · 运镜光影与克制微表演</div><div class="kv-val">${esc(m.camera_angle_and_movement)}<br/>${esc(m.natural_acting_subtext)}</div></div>
          </div>

          <div class="filmstrip-grid">
            <div class="frame-cell">
              <div class="frame-time">▶ START KEYFRAME [Frame 01 · 0.00s] (05文生图靶心)</div>
              <div style="font-size:12.5px;">${esc(s.start_frame.pose_and_expression)}</div>
            </div>
            <div class="frame-cell">
              <div class="frame-time">◆ MID-BEAT / APEX [Frame ${mid.frame_index || 16} · ${mid.timestamp_sec || 0.7}s]</div>
              <div style="font-size:12.5px;">${esc(mid.pose_and_expression || "")}</div>
              <div style="font-size:11.5px;color:#52d1c2;margin-top:4px;">🔊 ${esc(mid.sync_sound_cue || "")}</div>
            </div>
            <div class="frame-cell">
              <div class="frame-time">■ END KEYFRAME [Frame ${s.end_frame.frame_index} · ${s.end_frame.timestamp_sec}s] (切点守恒锚)</div>
              <div style="font-size:12.5px;">${esc(s.end_frame.pose_and_expression)}</div>
            </div>
          </div>

          <div class="inline-edit-row">
            <label style="font-size:12px;color:var(--text-secondary);">台词:</label>
            <input type="text" class="form-input" style="max-width:250px;" id="edit-narr-${s.shot_id}" value="${esc(s.narration)}" placeholder="无台词纯呼吸/拟音镜" />
            <label style="font-size:12px;color:var(--text-secondary);">时长(s):</label>
            <input type="number" class="form-input" style="max-width:78px;" id="edit-dur-${s.shot_id}" value="${s.duration_budget.final_duration_sec}" min="1.0" max="5.0" step="0.1" />
            <label style="font-size:12px;color:var(--text-secondary);">朝向:</label>
            <select class="form-select" style="max-width:130px;" id="edit-angle-${s.shot_id}">
              ${["front", "3_4_front", "side_profile", "3_4_back", "back"]
                .map((ang) => `<option value="${ang}" ${s.spatial_blocking.body_view_angle === ang ? "selected" : ""}>${ang}</option>`)
                .join("")}
            </select>
            <select class="form-select" style="max-width:165px;" id="edit-kf-${s.shot_id}">
              <option value="single_start_frame" ${m.which_keyframe_strategy === "single_start_frame" ? "selected" : ""}>单首帧 (Frame 01)</option>
              <option value="first_and_last_frames" ${m.which_keyframe_strategy === "first_and_last_frames" ? "selected" : ""}>首尾双关键帧 (01+N)</option>
            </select>
            <button class="btn btn-secondary btn-sm btn-save-shot-script" data-shot-id="${s.shot_id}">保存并重算全局时间码</button>
          </div>
        </section>
      `;
    })
    .join("");

  return `
    <div class="section-card">
      <div class="section-card-header">
        <h3 class="section-card-title">全片非均等心跳时长波形条 (总计 ${totalSec.toFixed(1)}s · ${Math.round(totalSec * 24)} 帧 @ 24fps)</h3>
        <span class="pill pill-amber">黄金前 3.0s 钩子密度已锁定</span>
      </div>
      <div class="pacing-bar-wrap"><div class="pacing-bar">${segsHtml}</div></div>
    </div>
    ${cardsHtml}
  `;
}

function renderTabCharacters(p) {
  const bible = p.asset_bible;
  if (!bible || !bible.characters || !bible.characters.length) {
    return `<div class="section-card">尚未生成角色三视图与声学资产（请先确认关卡 1 或等待自动推进）。</div>`;
  }

  const vocalMap = {};
  (p.vocal_profiles || []).forEach((v) => {
    vocalMap[v.character_id] = v;
  });

  return bible.characters
    .map((c) => {
      const voc = vocalMap[c.character_id];
      const accHtml = (c.accessories || [])
        .map(
          (a) => `
          <div class="kv-box">
            <div class="kv-label">${esc(a.name)} · 部位锁 [${esc(a.wear_location)}]</div>
            <div class="kv-val">${esc(a.material_and_detail)}<br/><span style="font-size:11px;color:var(--text-muted);">可见朝向: ${esc(a.visible_angles.join(", "))}</span></div>
          </div>
        `
        )
        .join("");

      const propHtml = (c.carried_props || [])
        .map(
          (pr) => `
          <div class="kv-grid" style="margin-top:8px;">
            <div class="kv-box">
              <div class="kv-label">${pr.is_chekhov_gun ? "★ 契诃夫核心伏笔信物" : "随身道具"} · ${esc(pr.name)}</div>
              <div class="kv-val"><strong>人体比例尺：</strong>${esc(pr.scale_reference)}<br/>${esc(pr.visual_detail)}</div>
            </div>
            <div class="kv-box">
              <div class="kv-label">① 常驻挂载态 (CARRIED STATE)</div>
              <div class="kv-val">${esc(pr.carried_state_desc)}</div>
            </div>
            <div class="kv-box">
              <div class="kv-label">② 手持激活态 (ACTIVE HELD TOPOLOGY)</div>
              <div class="kv-val">${esc(pr.active_held_state_desc)}</div>
            </div>
          </div>
        `
        )
        .join("");

      const vocalHtml = voc
        ? `
          <div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border-subtle);">
            <div class="kv-label" style="margin-bottom:8px;">08 角色五维声学基因锁 (VOCAL DNA · Anchor: ${esc(voc.voice_anchor_id)})</div>
            <div class="kv-grid">
              <div class="kv-box"><div class="kv-label">生理共鸣与声带颗粒度</div><div class="kv-val">${esc(voc.resonance_and_timbre)}</div></div>
              <div class="kv-box"><div class="kv-label">基频区间与语速基线</div><div class="kv-val">${esc(voc.pitch_and_tempo_baseline)}</div></div>
              <div class="kv-box"><div class="kv-label">句尾语调收音习惯 (Cadence)</div><div class="kv-val">${esc(voc.cadence_habit)}</div></div>
            </div>
          </div>
        `
        : "";

      return `
        <section class="section-card">
          <div class="section-card-header">
            <div>
              <strong style="font-size:16px;">${esc(c.name)}</strong>
              <span class="pill pill-amber" style="margin-left:8px;">${esc(c.role_type)}</span>
            </div>
            <span class="pill pill-teal">1440x960 正/侧/背正交三视图已锚定</span>
          </div>

          ${
            c.turnaround_image_url
              ? `<img src="${esc(c.turnaround_image_url)}" alt="${esc(c.name)} 标准正侧背三视图" class="turnaround-hero js-lightbox-trigger" style="margin-bottom:14px;" />`
              : ""
          }

          <div class="kv-grid" style="margin-bottom:12px;">
            <div class="kv-box"><div class="kv-label">骨相体态与左右面部印记</div><div class="kv-val">${esc(c.anatomy_and_silhouette)}</div></div>
            <div class="kv-box"><div class="kv-label">正/侧/背三面发型拓扑 (防背面画脸)</div><div class="kv-val"><strong>正:</strong> ${esc(c.hair_front)}<br/><strong>侧:</strong> ${esc(c.hair_side)}<br/><strong>背:</strong> ${esc(c.hair_back)}</div></div>
            <div class="kv-box"><div class="kv-label">内外三层服饰结构 (窄袖防穿模设计)</div><div class="kv-val">${esc(c.wardrobe_layered)}</div></div>
          </div>

          <div class="kv-label" style="margin-bottom:6px;">固定佩戴配饰清单 (含视角可见性过滤规则)</div>
          <div class="kv-grid" style="margin-bottom:12px;">${accHtml}</div>

          <div class="kv-label">随身物品双状态设定卡</div>
          ${propHtml}
          ${vocalHtml}

          <div class="inline-edit-row">
            <input type="text" class="form-input" style="max-width:380px;" id="char-note-${esc(c.character_id)}" placeholder="输入服饰、配饰或三视图微调指令…" />
            <button class="btn btn-secondary btn-sm btn-reroll-char" data-char-id="${esc(c.character_id)}">单独重抽 1440x960 角色三视图</button>
          </div>
        </section>
      `;
    })
    .join("");
}

function renderTabScenes(p) {
  const bible = p.asset_bible;
  if (!bible || !bible.scenes || !bible.scenes.length) {
    return `<div class="section-card">尚未生成三维罗盘场景空镜母版（请先确认关卡 1 或等待自动推进）。</div>`;
  }

  return bible.scenes
    .map((sc) => {
      const compassEntries = Object.entries(sc.compass_topology || {})
        .map(
          ([k, v]) => `
          <div class="kv-box">
            <div class="kv-label">罗盘方位 · ${esc(k.toUpperCase())}</div>
            <div class="kv-val">${esc(v)}</div>
          </div>
        `
        )
        .join("");

      return `
        <section class="section-card">
          <div class="section-card-header">
            <h3 class="section-card-title">${esc(sc.name)} · 无人空镜母版 (Master Scene Plate)</h3>
            <span class="pill pill-teal">东南西北空间坐标已锁死</span>
          </div>
          ${
            sc.master_plate_image_url
              ? `<img src="${esc(sc.master_plate_image_url)}" alt="${esc(sc.name)} 空镜母版" class="turnaround-hero js-lightbox-trigger" style="max-height:520px;object-fit:contain;margin-bottom:14px;" />`
              : ""
          }
          <div class="kv-label" style="margin-bottom:6px;">三维空间罗盘拓扑 (切机位绝不门窗乱飞)</div>
          <div class="kv-grid" style="margin-bottom:12px;">${compassEntries}</div>

          <div class="kv-label" style="margin-bottom:6px;">前 / 中 / 后三层景深陈设与声学地面</div>
          <div class="kv-grid">
            <div class="kv-box"><div class="kv-label">前景虚化遮挡层 (Foreground)</div><div class="kv-val">${esc(sc.foreground_layer)}</div></div>
            <div class="kv-box"><div class="kv-label">中景实体交互区 (Midground)</div><div class="kv-val">${esc(sc.midground_interactive_props)}</div></div>
            <div class="kv-box"><div class="kv-label">远景烟火生活痕迹 (Background)</div><div class="kv-val">${esc(sc.background_world_details)}</div></div>
            <div class="kv-box"><div class="kv-label">主辅光源色温与空气介质</div><div class="kv-val">${esc(sc.lighting_and_atmosphere)}</div></div>
          </div>

          <div class="inline-edit-row">
            <input type="text" class="form-input" style="max-width:380px;" id="scene-note-${esc(sc.scene_id)}" placeholder="补充中景陈设、光影色温或细节要求…" />
            <button class="btn btn-secondary btn-sm btn-reroll-scene" data-scene-id="${esc(sc.scene_id)}">单独重抽场景空镜母版</button>
          </div>
        </section>
      `;
    })
    .join("");
}

function renderTabKeyframes(p) {
  const shots = p.shots || [];
  const hasAnyImg = shots.some((s) => s.start_keyframe_url);
  if (!hasAnyImg) {
    return `<div class="section-card">尚未生成分镜关键帧（请先锁定关卡 2 角色三视图与场景母版，或等待自动执行）。</div>`;
  }

  const stripBanner = p.strip_audit
    ? `
      <div class="section-card" style="border-color:rgba(42,157,143,0.45);">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <strong style="color:#52d1c2;">✓ 06 作画监督「连环画拼条审片 (Pairwise Strip Continuity Audit)」全部通过 (${p.strip_audit.checked_pairs} 组切镜对)</strong>
          <span class="pill pill-teal">零跳轴 · 零特征串染 · 道具状态守恒</span>
        </div>
        <div style="font-size:12px;color:var(--text-secondary);margin-top:6px;">
          ${(p.strip_audit.axis_and_eyeline_notes || []).slice(0, 3).map(esc).join(" | ")}
        </div>
      </div>
    `
    : "";

  const cards = shots
    .map((s) => {
      const qa = s.qa_report;
      const isDual = Boolean(s.end_keyframe_url);
      const historyHtml =
        qa && qa.history_notes && qa.history_notes.length
          ? `<div style="background:rgba(224,159,62,0.12);border:1px solid rgba(224,159,62,0.35);border-radius:5px;padding:7px 9px;font-size:11.5px;color:var(--accent-amber);">
               <strong>⚡ 作画监督自动自愈闭环记录 (共 ${qa.attempt_count} 审达标)：</strong><br/>
               ${qa.history_notes.map(esc).join("<br/>")}
             </div>`
          : "";

      const coFrameBadge = s.co_framing && s.co_framing.is_multi_character
        ? `<span class="pill pill-amber">双人左右分仓防串色隔离</span>`
        : "";

      const qaGrid = qa
        ? `
          <div class="qa-bars">
            <div class="qa-metric"><div class="qa-metric-num">${qa.identity_and_props_score}</div><div class="qa-metric-lbl">人物配饰一致</div></div>
            <div class="qa-metric"><div class="qa-metric-num">${qa.anatomy_and_anticlipping_score}</div><div class="qa-metric-lbl">解剖零穿模</div></div>
            <div class="qa-metric"><div class="qa-metric-num">${qa.spatial_and_pose_naturalness_score}</div><div class="qa-metric-lbl">透视接地自然</div></div>
            <div class="qa-metric"><div class="qa-metric-num">${qa.scene_richness_and_lighting_score}</div><div class="qa-metric-lbl">场景光影丰满</div></div>
            <div class="qa-metric"><div class="qa-metric-num">${qa.i2v_motion_readiness_score}</div><div class="qa-metric-lbl">I2V运镜余量</div></div>
          </div>
        `
        : "";

      return `
        <article class="shot-card">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
            <div>
              <strong>S${String(s.shot_id).padStart(2, "0")}</strong>
              <span class="pill">${esc(s.six_w_one_h.which_shot_size)} · ${s.duration_budget.final_duration_sec}s</span>
              <span class="pill">${esc(s.spatial_blocking.body_view_angle)}</span>
              ${coFrameBadge}
            </div>
            <span class="pill ${isDual ? "pill-crimson" : "pill-teal"}">${isDual ? "首尾双关键帧" : "单首帧"}</span>
          </div>

          <div class="keyframe-pair ${isDual ? "dual" : "single"}">
            ${
              s.start_keyframe_url
                ? `<div class="keyframe-img-wrap"><img src="${esc(s.start_keyframe_url)}" alt="Shot ${s.shot_id} Start Keyframe" class="js-lightbox-trigger" /></div>`
                : ""
            }
            ${
              s.end_keyframe_url
                ? `<div class="keyframe-img-wrap"><img src="${esc(s.end_keyframe_url)}" alt="Shot ${s.shot_id} End Keyframe" class="js-lightbox-trigger" /></div>`
                : ""
            }
          </div>

          ${qaGrid}
          ${historyHtml}

          <div style="font-size:12px;color:var(--text-secondary);">
            <strong>空间站位与接地：</strong>${esc(s.spatial_blocking.ground_contact_and_shadow.slice(0, 68))}…<br/>
            <strong>防穿模解算：</strong>${esc(s.anticlipping_pose.limb_prop_separation_rule.slice(0, 74))}…
          </div>

          <details style="font-size:11.5px;color:var(--text-muted);">
            <summary style="cursor:pointer;color:var(--text-secondary);">查看视角裁剪锚点 &amp; 结构化文生图 Prompt</summary>
            <pre style="white-space:pre-wrap;background:var(--bg-surface-2);padding:8px;border-radius:4px;font-family:var(--font-mono);font-size:11px;">${esc(s.start_keyframe_prompt)}</pre>
          </details>

          <div class="inline-edit-row">
            <input type="text" class="form-input" style="flex:1;min-width:150px;" id="shot-fb-${s.shot_id}" placeholder="输入微调指令（如：加强轮廓背光、微调站位）…" />
            <button class="btn btn-secondary btn-sm btn-reroll-shot" data-shot-id="${s.shot_id}">单镜重抽并复审</button>
          </div>
        </article>
      `;
    })
    .join("");

  return `${stripBanner}<div class="storyboard-grid">${cards}</div>`;
}

function renderTabPostManifest(p) {
  if (!p.motion_blueprints || !p.motion_blueprints.length) {
    return `<div class="section-card">尚未编译 Phase 2 动态运镜、四轨声景与剪辑变速总单（请通过关卡 3 确认分镜关键帧）。</div>`;
  }

  const soundMap = {};
  (p.sound_blueprints || []).forEach((b) => {
    soundMap[b.shot_id] = b;
  });
  const editMap = {};
  (p.editorial_blueprints || []).forEach((e) => {
    editMap[e.shot_id] = e;
  });

  return p.motion_blueprints
    .map((mb) => {
      const sb = soundMap[mb.shot_id] || {};
      const eb = editMap[mb.shot_id] || {};
      const foleyRows = (sb.foley_cues || [])
        .map(
          (fc) => `<div style="font-size:12px;margin-bottom:3px;"><code>Frame ${fc.frame_index} (${fc.timestamp_sec}s, Pan:${esc(fc.stereo_pan)})</code> · <strong>${esc(fc.source_material)}</strong> → ${esc(fc.sound_description)}</div>`
        )
        .join("");

      return `
        <section class="section-card">
          <div class="section-card-header">
            <div>
              <strong style="font-size:15px;">SHOT ${String(mb.shot_id).padStart(2, "0")} 后期投产执行单</strong>
              <span class="pill pill-amber" style="margin-left:8px;">07模式: ${esc(mb.generation_mode)}</span>
              <span class="pill" style="margin-left:4px;">动态强度: ${mb.hyperparams.motion_intensity}/10 · 快门角: ${mb.hyperparams.shutter_angle_deg}°</span>
            </div>
            <span class="pill ${eb.audio_cut_type !== "straight_cut" ? "pill-teal" : ""}">${esc(eb.audio_cut_type)} (${eb.audio_offset_sec}s)</span>
          </div>

          <div class="kv-grid">
            <div class="kv-box">
              <div class="kv-label">07 去静态三段式时序 I2V/KF2V 提示词</div>
              <div class="kv-val" style="font-size:12px;">${esc(mb.temporal_tri_slice_prompt)}</div>
            </div>
            <div class="kv-box">
              <div class="kv-label">07 牛顿三级物理联动 (眼先动 → 配饰滞后4-8帧 → 高光扫掠)</div>
              <div class="kv-val" style="font-size:12px;">
                ① ${esc(mb.kinematics.primary_skeletal_drive.slice(0, 56))}…<br/>
                ② <span style="color:var(--accent-amber);">${esc(mb.kinematics.secondary_overlapping_motion)}</span><br/>
                ③ ${esc(mb.kinematics.tertiary_env_and_light_coupling.slice(0, 62))}…
              </div>
            </div>
            <div class="kv-box">
              <div class="kv-label">07 六自由度器械、真三维视差 &amp; 刚体防弯曲锁</div>
              <div class="kv-val" style="font-size:12px;">
                器械: <code>${esc(mb.camera_rig.rig_type)}</code> | ${esc(mb.camera_rig.counterbalance_rule_applied)}<br/>
                <span style="color:#52d1c2;">${esc(mb.rigid_prop_guardrail)}</span>
              </div>
            </div>
            <div class="kv-box">
              <div class="kv-label">08 生理受力气口台本 &amp; 空间混响 (${esc(sb.spatial_reverb_preset)})</div>
              <div class="kv-val" style="font-size:12px;">
                <code>${esc(sb.lip_sync_mode)}</code><br/>
                ${esc(sb.physiological_acting_script)}<br/>
                ${sb.has_music_drop ? `<strong style="color:#f0807c;">🔇 ${esc(sb.score_and_music_drop)}</strong>` : `<span style="color:var(--text-secondary);">${esc(sb.score_and_music_drop)}</span>`}
              </div>
            </div>
            <div class="kv-box">
              <div class="kv-label">08 材质联动帧同步拟音表 (Hard-Sync Foley)</div>
              <div class="kv-val">${foleyRows}</div>
            </div>
            <div class="kv-box">
              <div class="kv-label">09 手术刀黄金帧窗、曲线变速 &amp; 安全区字幕</div>
              <div class="kv-val" style="font-size:12px;">
                精选帧窗: <code>Frame ${eb.sweet_spot_in_frame} → Frame ${eb.sweet_spot_out_frame} (${eb.effective_trimmed_sec}s)</code><br/>
                变速曲线: ${esc(eb.speed_ramp_curve)}<br/>
                底部18%-22%安全区字幕: ${(eb.safe_zone_subtitles || []).map((t) => `<span class="pill pill-amber">${esc(t)}</span>`).join(" ") || "<span class='pill'>无字幕净画面</span>"}
              </div>
            </div>
          </div>
        </section>
      `;
    })
    .join("");
}

function renderTabScreeningRoom(p) {
  const shots = p.shots || [];
  if (!shots.length || !shots.some((s) => s.start_keyframe_url)) {
    return `<div class="section-card">请先完成 Phase 1 分镜关键帧生图（关卡 3），随后即可在此启动本地 Google Flow 真视频生成、手动导入 .mp4 片段或一键合成最终母带成片。</div>`;
  }

  const bpMap = {};
  (p.motion_blueprints || []).forEach((b) => {
    bpMap[b.shot_id] = b;
  });

  const errorBanner = p.error_message
    ? `<div style="background:rgba(217,83,79,0.14);border:1px solid rgba(217,83,79,0.5);border-radius:6px;padding:10px 12px;margin-bottom:14px;font-size:12.5px;color:#ff9b97;">
         <strong>⚠️ 浏览器交互提示：</strong> ${esc(p.error_message)}
       </div>`
    : "";

  const masterPlayerHtml = p.final_video_url
    ? `
      <div style="display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start;margin-top:12px;">
        <video src="${esc(p.final_video_url)}" controls playsinline style="max-height:520px;max-width:100%;border-radius:8px;border:1px solid var(--border-subtle);background:#000;"></video>
        <div style="flex:1;min-width:260px;">
          <div class="kv-box" style="margin-bottom:10px;">
            <div class="kv-label">母带成片规格 (FINAL MASTER)</div>
            <div class="kv-val">H.264 (<code>yuv420p</code> · 24fps) + 44.1kHz Stereo AAC<br/>已注入：角色神经配音 + 帧同步金属/银铃拟音 + 跨镜风雪底噪 + Music Drop 侧链闪避 + 底部黄金安全区字幕</div>
          </div>
          <div style="display:flex;gap:10px;flex-wrap:wrap;">
            <a href="/api/projects/${esc(p.project_id)}/final-video" class="btn btn-primary" download>⬇ 下载最终成片 (.mp4)</a>
            <button type="button" id="btn-recompose-master" class="btn btn-secondary">🎞️ 重新合成配音字幕母带</button>
          </div>
        </div>
      </div>
    `
    : `
      <div style="padding:18px;background:var(--bg-surface-2);border-radius:8px;font-size:13px;color:var(--text-secondary);margin-top:10px;">
        尚未合成最终成片 <code>final_master.mp4</code>。你可以点击上方<strong>「🚀 一键渲染全片视频并压制成片」</strong>，或在下方逐镜调用 Google Flow / 手动拖入从 Google Flow 网页下载的 <code>.mp4</code> 视频片段后点击<strong>「🎞️ 合成最终母带成片」</strong>。
      </div>
    `;

  const shotVideoCards = shots
    .map((s) => {
      const bp = bpMap[s.shot_id] || {};
      const isDual = Boolean(s.end_keyframe_url);
      const flowPrompt = bp.flow_english_prompt || bp.temporal_tri_slice_prompt || "";

      const mediaPreview = s.video_clip_url
        ? `<video src="${esc(s.video_clip_url)}" controls loop playsinline style="width:100%;max-height:340px;border-radius:6px;background:#000;"></video>`
        : `
          <div class="keyframe-pair ${isDual ? "dual" : "single"}">
            ${s.start_keyframe_url ? `<div class="keyframe-img-wrap"><img src="${esc(s.start_keyframe_url)}" alt="Start" class="js-lightbox-trigger" /></div>` : ""}
            ${s.end_keyframe_url ? `<div class="keyframe-img-wrap"><img src="${esc(s.end_keyframe_url)}" alt="End" class="js-lightbox-trigger" /></div>` : ""}
          </div>
        `;

      return `
        <article class="shot-card">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
            <div>
              <strong>S${String(s.shot_id).padStart(2, "0")}</strong>
              <span class="pill">${s.duration_budget.final_duration_sec}s</span>
              <span class="pill ${isDual ? "pill-crimson" : "pill-teal"}">${isDual ? "Flow Frames: 首帧 + 尾帧双锁" : "Flow Frames: 单起始帧"}</span>
            </div>
            <span class="pill ${s.video_clip_url ? "pill-amber" : ""}">${s.video_clip_url ? "✓ 视频片段已就绪" : "待生成/上传视频"}</span>
          </div>

          ${mediaPreview}

          <div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
              <label class="kv-label" for="flow-prompt-${s.shot_id}">Google Flow 原生英文动态提示词 (含中文原声对白指令)</label>
              <button type="button" class="btn btn-secondary btn-sm btn-copy-flow-prompt" data-shot-id="${s.shot_id}" style="padding:2px 8px;font-size:11px;">📋 复制</button>
            </div>
            <textarea id="flow-prompt-${s.shot_id}" class="form-textarea" rows="3" style="font-size:11.5px;font-family:var(--font-mono);">${esc(flowPrompt)}</textarea>
          </div>

          <div class="inline-edit-row" style="justify-content:space-between;">
            <button type="button" class="btn btn-primary btn-sm btn-render-shot-video" data-shot-id="${s.shot_id}">⚡ 调用引擎生成本镜视频</button>
            <label class="btn btn-secondary btn-sm" style="cursor:pointer;margin:0;">
              📤 手动上传 Flow .mp4
              <input type="file" accept="video/mp4,video/*" class="input-upload-shot-video" data-shot-id="${s.shot_id}" style="display:none;" />
            </label>
          </div>
        </article>
      `;
    })
    .join("");

  return `
    ${errorBanner}
    <section class="section-card">
      <div class="section-card-header">
        <div>
          <h3 class="section-card-title">🎬 07/08/09 母带成片放映室 &amp; Phase 2 全自动合成总控</h3>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button type="button" id="btn-run-phase2-all" class="btn btn-primary btn-sm">🚀 一键渲染全片视频并压制成片</button>
          <button type="button" id="btn-recompose-top" class="btn btn-secondary btn-sm">🎞️ 合成最终母带成片 (PyAV)</button>
        </div>
      </div>
      ${masterPlayerHtml}
    </section>

    <div class="storyboard-grid">${shotVideoCards}</div>
  `;
}

/* ============================================================================
   Event Handlers for Surgical Edits, Rerolls, Video Upload & Lightbox
   ============================================================================ */

function bindScreeningRoomHandlers() {
  const runAllBtn = document.getElementById("btn-run-phase2-all");
  if (runAllBtn) {
    runAllBtn.addEventListener("click", async () => {
      runAllBtn.disabled = true;
      runAllBtn.textContent = "已启动 Phase 2 队列…";
      try {
        await apiFetch(`/api/projects/${state.currentProjectId}/run-phase2?background=true`, {
          method: "POST",
        });
        await refreshCurrentProject();
      } catch (err) {
        alert(`启动 Phase 2 失败: ${err.message}`);
        runAllBtn.disabled = false;
      }
    });
  }

  ["btn-recompose-top", "btn-recompose-master"].forEach((id) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      btn.textContent = "正在合成四轨声画母带…";
      try {
        state.project = await apiFetch(`/api/projects/${state.currentProjectId}/recompose`, {
          method: "POST",
        });
        renderAll();
      } catch (err) {
        alert(`合片失败: ${err.message}`);
      } finally {
        btn.disabled = false;
      }
    });
  });

  document.querySelectorAll(".btn-copy-flow-prompt").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const shotId = btn.dataset.shotId;
      const txt = document.getElementById(`flow-prompt-${shotId}`).value;
      try {
        await navigator.clipboard.writeText(txt);
        btn.textContent = "✓ 已复制";
        setTimeout(() => {
          btn.textContent = "📋 复制";
        }, 1400);
      } catch (_) {
        // ignore clipboard restrictions
      }
    });
  });

  document.querySelectorAll(".btn-render-shot-video").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const shotId = Number(btn.dataset.shotId);
      const promptOverride = document.getElementById(`flow-prompt-${shotId}`).value;
      btn.disabled = true;
      btn.textContent = "正在生成视频…";
      try {
        state.project = await apiFetch(
          `/api/projects/${state.currentProjectId}/shots/${shotId}/reroll-video`,
          {
            method: "POST",
            body: JSON.stringify({ prompt_override: promptOverride, auto_recompose: true }),
          }
        );
        renderAll();
      } catch (err) {
        alert(`单镜视频生成提示: ${err.message}`);
      } finally {
        btn.disabled = false;
        btn.textContent = "⚡ 调用引擎生成本镜视频";
      }
    });
  });

  document.querySelectorAll(".input-upload-shot-video").forEach((inp) => {
    inp.addEventListener("change", async () => {
      if (!inp.files || !inp.files.length) return;
      const shotId = Number(inp.dataset.shotId);
      const formData = new FormData();
      formData.append("file", inp.files[0]);
      const res = await fetch(
        `/api/projects/${state.currentProjectId}/shots/${shotId}/upload-video?auto_recompose=true`,
        { method: "POST", body: formData }
      );
      if (!res.ok) {
        const msg = await res.text();
        alert(`上传视频失败: ${msg}`);
        return;
      }
      state.project = await res.json();
      renderAll();
    });
  });
}

function bindScriptEditHandlers() {
  document.querySelectorAll(".btn-save-shot-script").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const shotId = Number(btn.dataset.shotId);
      const narration = document.getElementById(`edit-narr-${shotId}`).value;
      const durationSec = Number(document.getElementById(`edit-dur-${shotId}`).value);
      const bodyViewAngle = document.getElementById(`edit-angle-${shotId}`).value;
      const kfStrategy = document.getElementById(`edit-kf-${shotId}`).value;
      btn.disabled = true;
      try {
        state.project = await apiFetch(`/api/projects/${state.currentProjectId}/shots/${shotId}`, {
          method: "PATCH",
          body: JSON.stringify({
            narration,
            duration_sec: durationSec,
            body_view_angle: bodyViewAngle,
            keyframe_strategy: kfStrategy,
          }),
        });
        renderAll();
      } catch (err) {
        alert(`保存失败: ${err.message}`);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function bindCharacterHandlers() {
  document.querySelectorAll(".btn-reroll-char").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const charId = btn.dataset.charId;
      const note = document.getElementById(`char-note-${charId}`).value;
      btn.disabled = true;
      btn.textContent = "正在重绘三视图…";
      try {
        state.project = await apiFetch(
          `/api/projects/${state.currentProjectId}/characters/${charId}/reroll`,
          { method: "POST", body: JSON.stringify({ custom_note: note }) }
        );
        renderAll();
      } catch (err) {
        alert(`重抽失败: ${err.message}`);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function bindSceneHandlers() {
  document.querySelectorAll(".btn-reroll-scene").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const sceneId = btn.dataset.sceneId;
      const note = document.getElementById(`scene-note-${sceneId}`).value;
      btn.disabled = true;
      btn.textContent = "正在重绘场景母版…";
      try {
        state.project = await apiFetch(
          `/api/projects/${state.currentProjectId}/scenes/${sceneId}/reroll`,
          { method: "POST", body: JSON.stringify({ custom_note: note }) }
        );
        renderAll();
      } catch (err) {
        alert(`重抽失败: ${err.message}`);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function bindKeyframeHandlers() {
  document.querySelectorAll(".btn-reroll-shot").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const shotId = Number(btn.dataset.shotId);
      const fb = document.getElementById(`shot-fb-${shotId}`).value;
      btn.disabled = true;
      btn.textContent = "重抽并送质检…";
      try {
        state.project = await apiFetch(
          `/api/projects/${state.currentProjectId}/shots/${shotId}/reroll`,
          { method: "POST", body: JSON.stringify({ feedback: fb }) }
        );
        renderAll();
      } catch (err) {
        alert(`单镜重抽失败: ${err.message}`);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function bindLightboxTriggers(root) {
  const modal = document.getElementById("modal-lightbox");
  const img = document.getElementById("lightbox-img");
  root.querySelectorAll(".js-lightbox-trigger").forEach((el) => {
    el.addEventListener("click", () => {
      img.src = el.src;
      modal.showModal();
    });
  });
}

/* ============================================================================
   Live SSE Telemetry & Project History Sync
   ============================================================================ */

function renderLogs() {
  const feed = document.getElementById("agent-log-feed");
  const logs = state.project ? state.project.agent_logs || [] : [];
  feed.innerHTML = logs
    .slice()
    .reverse()
    .map((ev) => {
      const t = (ev.timestamp || "").slice(11, 19);
      return `
        <div class="log-entry ${esc(ev.level)}">
          <div class="log-meta">
            <span>${esc(ev.agent_name)}</span>
            <span>${esc(t)}</span>
          </div>
          <div>${esc(ev.message)}</div>
        </div>
      `;
    })
    .join("");
}

function connectSSE(projectId) {
  if (state.sse) {
    state.sse.close();
    state.sse = null;
  }
  const es = new EventSource(`/api/projects/${projectId}/stream`);
  es.onmessage = async (evt) => {
    try {
      const data = JSON.parse(evt.data);
      if (data.type === "connected" || data.type === "agent_event" || data.type === "state_sync") {
        await refreshCurrentProject();
        await loadProjectHistory();
      }
    } catch (_) {
      // ignore malformed keepalive
    }
  };
  state.sse = es;
}

async function refreshCurrentProject() {
  if (!state.currentProjectId) return;
  state.project = await apiFetch(`/api/projects/${state.currentProjectId}`);
  renderAll();
}

function renderAll() {
  renderAgentRail();
  renderGateBanner();
  renderWorkbench();
  renderLogs();
}

function setActiveTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === tabId);
  });
  renderWorkbench();
}

async function loadProjectHistory() {
  const list = await apiFetch("/api/projects");
  const container = document.getElementById("project-history-list");
  if (!list.length) {
    container.innerHTML = `<div style="font-size:12px;color:var(--text-muted);">暂无历史工程</div>`;
    return;
  }
  container.innerHTML = list
    .map(
      (item) => `
      <button type="button" class="project-item ${item.project_id === state.currentProjectId ? "selected" : ""}" data-pid="${esc(item.project_id)}">
        <div class="project-item-title">${esc(item.title || item.topic)}</div>
        <div class="project-item-meta">
          <span>${esc(item.aspect_ratio)} · ${item.shot_count}镜</span>
          <span>${esc(item.stage)}</span>
        </div>
      </button>
    `
    )
    .join("");

  container.querySelectorAll(".project-item").forEach((el) => {
    el.addEventListener("click", async () => {
      state.currentProjectId = el.dataset.pid;
      await refreshCurrentProject();
      connectSSE(state.currentProjectId);
      await loadProjectHistory();
    });
  });
}

async function initSettingsModal() {
  const modal = document.getElementById("modal-settings");
  const statusPill = document.getElementById("vendor-status-pill");
  const flowStatusBox = document.getElementById("flow-cdp-status-box");

  async function syncVendorPill() {
    const cfg = await apiFetch("/api/settings/providers");
    statusPill.textContent = `引擎: T2I=${cfg.image_vendor} / Video=${cfg.video_vendor}`;
    document.getElementById("cfg-llm-vendor").value = cfg.llm_vendor;
    document.getElementById("cfg-img-vendor").value = cfg.image_vendor;
    document.getElementById("cfg-vid-vendor").value = cfg.video_vendor;
    document.getElementById("cfg-tts-vendor").value = cfg.tts_vendor;
    document.getElementById("cfg-flow-cdp").value = cfg.flow_cdp_url || "http://127.0.0.1:9222";
  }

  async function checkFlowStatus() {
    const cdp = document.getElementById("cfg-flow-cdp").value.trim();
    flowStatusBox.textContent = "正在探测本机 Chrome CDP 端口…";
    try {
      const st = await apiFetch(`/api/flow-browser/status?cdp_url=${encodeURIComponent(cdp)}`);
      flowStatusBox.style.color = st.connected ? "#52d1c2" : "#ff9b97";
      flowStatusBox.textContent = st.message;
      return st;
    } catch (err) {
      flowStatusBox.style.color = "#ff9b97";
      flowStatusBox.textContent = `探测异常: ${err.message}`;
      return null;
    }
  }

  await syncVendorPill();

  document.getElementById("btn-check-flow-cdp").addEventListener("click", checkFlowStatus);

  document.getElementById("btn-quick-flow").addEventListener("click", async () => {
    const res = await apiFetch("/api/flow-browser/enable", {
      method: "POST",
      body: JSON.stringify({ enable_image_nano_banana: true, enable_video_flow: true }),
    });
    await syncVendorPill();
    if (!res.flow_status.connected) {
      flowStatusBox.style.color = "#ff9b97";
      flowStatusBox.textContent = res.flow_status.message;
      modal.showModal();
    } else {
      alert(res.flow_status.message);
    }
  });

  document.getElementById("btn-open-settings").addEventListener("click", async () => {
    await syncVendorPill();
    modal.showModal();
  });
  document.getElementById("btn-close-settings").addEventListener("click", () => modal.close());

  document.getElementById("btn-save-settings").addEventListener("click", async () => {
    const patch = {
      llm_vendor: document.getElementById("cfg-llm-vendor").value,
      image_vendor: document.getElementById("cfg-img-vendor").value,
      video_vendor: document.getElementById("cfg-vid-vendor").value,
      tts_vendor: document.getElementById("cfg-tts-vendor").value,
      flow_cdp_url: document.getElementById("cfg-flow-cdp").value.trim() || "http://127.0.0.1:9222",
      volc_api_key: document.getElementById("cfg-volc-key").value || undefined,
      dashscope_api_key: document.getElementById("cfg-dash-key").value || undefined,
      kling_access_key: document.getElementById("cfg-kling-ak").value || undefined,
      kling_secret_key: document.getElementById("cfg-kling-sk").value || undefined,
      openai_api_key: document.getElementById("cfg-openai-key").value || undefined,
      gemini_api_key: document.getElementById("cfg-gemini-key").value || undefined,
    };
    await apiFetch("/api/settings/providers", {
      method: "PUT",
      body: JSON.stringify(patch),
    });
    await syncVendorPill();
    modal.close();
  });
}

async function bootstrap() {
  renderAgentRail();

  // Preset chips
  document.querySelectorAll(".chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.getElementById("input-topic").value = chip.dataset.preset;
    });
  });

  // Tabs
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
  });

  // Lightbox close on click
  const lightbox = document.getElementById("modal-lightbox");
  lightbox.addEventListener("click", () => lightbox.close());

  // Export manifest top button
  document.getElementById("btn-export-manifest").addEventListener("click", () => {
    if (state.currentProjectId) {
      window.open(`/api/projects/${state.currentProjectId}/manifest`, "_blank");
    }
  });

  // Create project button
  const createBtn = document.getElementById("btn-create-project");
  createBtn.addEventListener("click", async () => {
    const topic = document.getElementById("input-topic").value.trim();
    if (!topic) return;
    createBtn.disabled = true;
    createBtn.textContent = "开机立项中…";
    try {
      const created = await apiFetch("/api/projects?background=true", {
        method: "POST",
        body: JSON.stringify({
          topic,
          aspect_ratio: document.getElementById("select-aspect").value,
          target_duration_sec: Number(document.getElementById("input-duration").value),
          style_preset: document.getElementById("select-style").value,
          execution_mode: document.getElementById("select-mode").value,
        }),
      });
      state.currentProjectId = created.project_id;
      state.project = created;
      setActiveTab("tab-dramaturgy");
      connectSSE(created.project_id);
      await refreshCurrentProject();
      await loadProjectHistory();
    } catch (err) {
      alert(`立项失败: ${err.message}`);
    } finally {
      createBtn.disabled = false;
      createBtn.textContent = "开机立项 · 启动 9-Agent 协同";
    }
  });

  await initSettingsModal();
  await loadProjectHistory();

  // Auto-select latest project if any exists
  const existing = await apiFetch("/api/projects");
  if (existing.length > 0) {
    state.currentProjectId = existing[0].project_id;
    await refreshCurrentProject();
    connectSSE(state.currentProjectId);
    await loadProjectHistory();
  }

  // Safety poller while project is in any transient working stage
  const TRANSIENT_STAGES = new Set([
    "CREATED",
    "PLANNING_SCRIPT",
    "BUILDING_ASSETS",
    "GENERATING_STORYBOARD",
    "REVIEWING_STORYBOARD",
    "COMPILING_MANIFEST",
    "GENERATING_VIDEOS",
    "COMPOSITING_FINAL",
  ]);
  setInterval(async () => {
    if (state.currentProjectId && state.project && TRANSIENT_STAGES.has(state.project.stage)) {
      try {
        await refreshCurrentProject();
      } catch (_) {
        // ignore transient fetch errors
      }
    }
  }, 1000);

  document.body.dataset.studioReady = "true";
}

bootstrap();
