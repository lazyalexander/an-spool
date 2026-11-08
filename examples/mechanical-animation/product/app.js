// Domain UI submits explicit previews; the original daemon owns every attempt.
let token = location.hash.slice(1);
history.replaceState(null, '', location.pathname);
window.addEventListener('hashchange', () => { if (location.hash) {
    token = location.hash.slice(1);
    history.replaceState(null, '', location.pathname);
    byId('error').textContent = '';
    refresh();
} });
const byId = id => document.getElementById(id);
const stageNames = { 'mechanism': '几何与运动', 'appearance': '外观素材', 'mechanical-film': '动画与交付' };
const labels = { 'queued': '排队中', 'running-or-unconfirmed': '运行中或待核实', 'settled': '已结算', 'succeeded': '成功', 'failed': '失败', 'cancelled': '已取消', 'timed_out': '超时', 'accepted': '已验收', 'awaiting-acceptance': '待验收' };
const actions = { start: '运行', accept: '验收产物', cancel: '取消', pause: '暂停接单', resume: '恢复接单', unload: '卸载', krita: '交给 Krita' };
let pending = null;
async function request(path, value) { const response = await fetch(path, { method: value ? 'POST' : 'GET', headers: { Authorization: 'Bearer ' + token, ...(value ? { 'Content-Type': 'application/json' } : {}) }, ...(value ? { body: JSON.stringify(value) } : {}) }); const data = await response.json(); if (!response.ok)
    throw Error(data.error ?? '请从本地产品入口重新打开'); return data; }
async function preview(caseName, stage, operation) { try {
    const value = { case: caseName, stage, operation };
    const result = await request('/action', value);
    pending = { ...value, approve: result.approval_sha256 };
    byId('summary').textContent = `${caseName === 'steam' ? '蒸汽机' : '四缸发动机'} · ${stageNames[stage]} · ${actions[operation]}。执行时使用选定的本机工具，文件与图形权限以本次计划为准。`;
    byId('plan').textContent = JSON.stringify(result.plan, null, 2);
    byId('review').hidden = false;
    byId('review').scrollIntoView({ behavior: 'smooth' });
}
catch (error) {
    byId('error').textContent = error.message;
} }
function button(parent, text, callback) { const el = document.createElement('button'); el.textContent = text; el.onclick = callback; parent.append(el); }
async function refresh() { try {
    const data = await request('/view');
    byId('observation').href = data.observation_url;
    byId('connection').textContent = '本机已连接 · ' + new Date().toLocaleTimeString();
    byId('cases').replaceChildren();
    for (const [caseName, stages] of Object.entries(data.cases)) {
        const section = document.createElement('section');
        const heading = document.createElement('h2');
        heading.textContent = caseName === 'steam' ? '蒸汽机 · 主教学' : '四缸发动机 · 复用验证';
        section.append(heading);
        const table = document.createElement('table');
        let previousAccepted = true;
        for (const [name, stage] of Object.entries(stages)) {
            const task = data.snapshot.tasks.find(t => t.instance === stage.instance && t.run === stage.run);
            const instance = data.snapshot.instances.find(i => i.registration.path === stage.instance)?.view;
            const accepted = task?.native?.artifact_status === 'accepted';
            const row = document.createElement('tr');
            const title = document.createElement('td');
            title.textContent = stageNames[name];
            row.append(title);
            const state = document.createElement('td');
            state.textContent = accepted ? '已验收' : task ? `${labels[task.state] ?? task.state} · ${labels[task.outcome] ?? task.outcome ?? '等待结果'}` : previousAccepted ? '可开始' : '等待上一步验收';
            if (instance?.loaded === false) state.textContent += ' · 已卸载';
            else if (instance?.round_control?.mode === 'paused') state.textContent += ' · 已暂停接单';
            else if (instance?.round_control?.mode === 'suspended') state.textContent += ' · 已休眠';
            if (task?.resources?.available) {
                const r = task.resources;
                const usage = document.createElement('small');
                usage.textContent = ` · ${((r.cpu_user_ns + r.cpu_system_ns) / 1e9).toFixed(1)} s / ${(r.resident_bytes / 1048576).toFixed(1)} MB`;
                state.append(usage);
            }
            row.append(state);
            const controls = document.createElement('td');
            const add = op => button(controls, actions[op], () => preview(caseName, name, op));
            if (!task && previousAccepted && instance?.loaded && instance?.round_control?.mode === 'active')
                add('start');
            if (task?.state === 'settled' && task.outcome === 'succeeded' && !accepted)
                add('accept');
            if (task && task.state !== 'settled')
                add('cancel');
            if (accepted && name === 'mechanical-film')
                add('krita');
            if (instance?.loaded) {
                add(instance.round_control?.mode === 'paused' ? 'resume' : 'pause');
                if (!task || task.state === 'settled')
                    add('unload');
            }
            row.append(controls);
            table.append(row);
            previousAccepted = accepted;
        }
        section.append(table);
        byId('cases').append(section);
    }
}
catch (error) {
    byId('error').textContent = error.message;
} }
byId('confirm').onclick = async () => { if (!pending)
    return; byId('confirm').disabled = true; try {
    await request('/action', pending);
    pending = null;
    byId('review').hidden = true;
    byId('error').textContent = '';
    await refresh();
}
catch (error) {
    byId('error').textContent = error.message;
    byId('review').hidden = true;
    pending = null;
}
finally {
    byId('confirm').disabled = false;
} };
byId('dismiss').onclick = () => { pending = null; byId('review').hidden = true; };
refresh();
setInterval(refresh, 2000);
