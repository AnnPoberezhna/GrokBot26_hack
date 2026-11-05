(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
  const colors = ['#a4d3b6', '#bba6e7', '#e7bd8d', '#a2c3e3', '#dfaec9'];
  const state = { mode: localStorage.getItem('grokmesh-mode') || 'demo', data:null, filter:'all', view:'overview', search:'', zoom:1, selected:null, request:0 };
  let timer, toastTimer;
  const people = () => state.data?.developers || [];
  const name = id => id ? id.charAt(0).toUpperCase() + id.slice(1) : 'Base';
  const color = id => colors[Math.max(0, people().findIndex(d => d.dev_id === id)) % colors.length];
  const avatar = id => `<span class="avatar" style="color:${color(id)};background:${color(id)}22" title="${escape(name(id))}">${escape(id.slice(0,2).toUpperCase())}</span>`;
  const ago = timestamp => {
    const secs = Math.max(0, Math.floor((Date.now()/1000) - timestamp));
    return secs < 60 ? 'just now' : secs < 3600 ? `${Math.floor(secs/60)}m ago` : `${Math.floor(secs/3600)}h ago`;
  };
  function notify(text) { $('toast').textContent=text; $('toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('toast').hidden=true,2600); }
  function connection(text, error=false) {
    $('connection-label').innerHTML=`<span class="online-dot" style="background:${error?'var(--red)':'var(--lime)'}"></span><span>${escape(text)}</span>`;
    document.querySelector('.sidebar-footer').style.opacity=error?'.5':'1';
    $('broker-status').textContent=error?'Broker unavailable':'Broker connected';
  }
  async function load() {
    const request=++state.request;
    try {
      const response=await fetch(`/api/dashboard${state.mode==='demo'?'?demo=1':''}`, {cache:'no-store'});
      if (!response.ok) throw new Error(`Broker returned ${response.status}`);
      const data=await response.json();
      if (request!==state.request) return;
      state.data=data; $('notice').hidden=true;
      connection(state.mode==='demo'?'Sample workspace · isolated demo':'Connected · updates every 3s');
      render();
    } catch(error) {
      if (request!==state.request) return;
      connection('Connection interrupted',true);
      $('notice').textContent=`Could not refresh this workspace. ${error.message}. Your last view is preserved; retrying automatically.`;
      $('notice').hidden=false;
    } finally { clearTimeout(timer); timer=setTimeout(load, state.mode==='demo'?30000:3000); }
  }
  function render() {
    const data=state.data, m=data.metrics;
    $('metric-developers').textContent=String(m.developers).padStart(2,'0');
    $('metric-symbols').textContent=String(m.symbols).padStart(2,'0');
    $('metric-leases').textContent=String(m.leases).padStart(2,'0');
    $('metric-collisions').textContent=String(m.blocking+m.warnings).padStart(2,'0');
    document.querySelectorAll('.lease-bars i').forEach((bar,index)=>{bar.style.background=index<Math.min(m.leases,12)?'var(--lime)':'#3a4531';});
    $('metric-conflict-note').textContent=`${m.blocking} blocking · ${m.warnings} warnings`;
    $('metric-avatars').innerHTML=people().map(d=>avatar(d.dev_id)).join('');
    $('team-count').textContent=people().length;
    $('nav-count').textContent=data.collisions.length;
    $('collision-count').textContent=data.collisions.length;
    $('graph-badge').textContent=state.mode==='demo'?'DEMO CONTEXT':'LIVE CONTEXT';
    $('sync-label').textContent=state.mode==='demo'?'Sample graph · powered by the collision engine':`Last refreshed ${new Date(data.generated_at*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'})}`;
    $('mode-footer').textContent=state.mode==='demo'?'Demonstration workspace · sample data':'Live workspace · read-only dashboard';
    renderTeam(); renderGraph(); renderCollisions(); renderContracts();
  }
  function renderTeam() {
    $('team-list').innerHTML=people().length ? people().map(dev=>{
      const goals=dev.intents.map(i=>i.goal);
      const updated=Math.max(0,...dev.intents.map(i=>i.updated_at),...dev.leases.map(l=>l.heartbeat));
      const symbols=[...new Set([...dev.leases.map(l=>l.symbol_id),...dev.intents.flatMap(i=>[...i.produces,...i.modifies])])];
      return `<article class="team-member"><div class="member-heading">${avatar(dev.dev_id)}<span class="member-name">${escape(name(dev.dev_id))}<small>${dev.intents.length} active intent${dev.intents.length===1?'':'s'}</small></span><span class="member-status">${dev.leases.length?'Building':'Planning'}</span></div><p class="intent-goal">${escape(goals.join(' · ') || 'Editing shared code')}</p><div class="member-symbols">${symbols.slice(0,3).map(id=>`<button class="symbol-chip" data-symbol="${escape(id)}" title="${escape(id)}">${escape(id.split('.').slice(-2).join('.'))}</button>`).join('')}${symbols.length>3?`<span class="symbol-chip">+${symbols.length-3}</span>`:''}</div><div class="member-meta"><span>${dev.leases.length} active lease${dev.leases.length===1?'':'s'}</span><span>Updated ${ago(updated)}</span></div></article>`;
    }).join('') : '<div class="empty-state"><strong>The mesh is ready.</strong><br>Active teammates will appear here<br>as they declare their work.</div>';
  }
  function renderGraph() {
    const nodes=state.data.nodes.filter(n=>`${n.id} ${n.signature}`.toLowerCase().includes(state.search));
    const graph=$('code-graph'); $('graph-empty').hidden=nodes.length>0;
    if (!nodes.length) {
      graph.innerHTML='';
      $('graph-empty').querySelector('h3').textContent=state.search?'No matching symbols.':'Your shared graph starts here.';
      $('graph-empty').querySelector('p').textContent=state.search?'Try a different symbol name or clear your search.':'Sync a Python file through MCP to see your team’s work. Switch to Demo for a preview.';
    }
    const modules=[...new Set(nodes.map(n=>n.id.split('.').slice(0,-1).join('.')))];
    const order=m=>m.endsWith('.api')?0:m.endsWith('.auth')?1:m.endsWith('.tokens')?2:m.endsWith('.audit')?3:4;
    modules.sort((a,b)=>order(a)-order(b)||a.localeCompare(b));
    const columns=[[],[],[]]; modules.forEach((module,index)=>columns[index%3].push(...nodes.filter(n=>n.id.split('.').slice(0,-1).join('.')===module).sort((a,b)=>a.id.localeCompare(b.id))));
    const count=Math.max(3,...columns.map(c=>c.length)), height=count*85+65;
    const positions=new Map();
    columns.forEach((column,c)=>column.forEach((node,r)=>positions.set(node.id,{x:47+c*309,y:35+r*85+(c===1?13:0)})));
    const shown=state.data.edges.filter(e=>positions.has(e.src)&&positions.has(e.dst));
    graph.setAttribute('viewBox',`0 0 950 ${height}`);
    const paths=shown.map(edge=>{
      const a=positions.get(edge.src), b=positions.get(edge.dst), conflict=state.data.nodes.find(n=>n.id===edge.dst)?.collision;
      let path;
      if (a.x===b.x) path=`M ${a.x+104} ${a.y+62} C ${a.x+145} ${a.y+100}, ${b.x+145} ${b.y-35}, ${b.x+104} ${b.y}`;
      else {const forward=b.x>a.x, sx=a.x+(forward?208:0), tx=b.x+(forward?0:208), mid=(sx+tx)/2;
        path=`M ${sx} ${a.y+31} C ${mid} ${a.y+31}, ${mid} ${b.y+31}, ${tx} ${b.y+31}`;}
      return `<path class="graph-edge${conflict?' conflict-edge':''}" d="${path}" marker-end="url(#arrow-${conflict?'conflict':'base'})"/>`;
    }).join('');
    const boxes=nodes.map(node=>{
      const p=positions.get(node.id), parts=node.id.split('.'), title=parts.pop(), module=parts.join('.');
      const active=node.owners.length, owner=node.owners[0];
      return `<g class="graph-node${active?' active':''}${node.collision?' conflict':''}" transform="translate(${p.x},${p.y})" data-symbol="${escape(node.id)}" tabindex="0" role="button" aria-label="Inspect ${escape(node.id)}"><rect class="node-box" width="208" height="62" rx="6"/><text class="node-module" x="13" y="17">${escape(module.length>26?module.slice(0,24)+'…':module)}</text><circle class="node-dot" cx="191" cy="15" r="2.5" ${!active?'style="fill:#64745a"':''}/><text class="node-name" x="13" y="36">${escape(title.length>24?title.slice(0,22)+'…':title)}${node.kind==='class'?'':'()'}</text><text class="node-state" x="13" y="51">${node.collision?'Contract needs attention':active?'In progress':'Main branch'}</text>${owner?`<text class="node-owner" text-anchor="end" x="194" y="51" fill="${color(owner)}">${escape(name(owner))}</text>`:''}</g>`;
    }).join('');
    graph.innerHTML=`<defs><marker id="arrow-base" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#647753"/></marker><marker id="arrow-conflict" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#bb7968"/></marker></defs><g id="graph-scene">${paths}${boxes}</g>`;
    zoom();
    $('graph-summary').textContent=`${nodes.length}${state.data.metrics.symbols>state.data.nodes.length?' of '+state.data.metrics.symbols:''} nodes · ${shown.length} edges`;
  }
  function zoom() {
    const scene=$('graph-scene'); if (scene) {
      const h=Number($('code-graph').getAttribute('viewBox').split(' ')[3]);
      scene.setAttribute('transform',`translate(${475*(1-state.zoom)},${h/2*(1-state.zoom)}) scale(${state.zoom})`);
    }
    $('zoom-reset').textContent=`${Math.round(state.zoom*100)}%`;
  }
  const kindName = kind => ({same_symbol:'Same symbol, two intentions',broken_contract:'A contract is drifting',duplication:'Similar work, different names',intent_conflict:'Overlapping intentions'}[kind]||kind);
  function collisionDescription(report) {
    if(report.kind==='broken_contract') return `<code>${escape(report.caller_symbol_id)}</code> depends on a signature that changed. Agree on the contract before continuing.`;
    if(report.kind==='duplication') return 'Text search found related work in a teammate’s context. Review it together before building another version. <span class="unconfirmed">Unconfirmed match.</span>';
    return 'Two developers are working toward the same symbol. Coordinate ownership before the next edit.';
  }
  function renderCollisions() {
    const reports=state.data.collisions.filter(r=>state.filter==='all'||r.severity===state.filter);
    $('collision-list').innerHTML=reports.length?reports.map(report=>{
      const index=state.data.collisions.indexOf(report);
      return `<article class="collision-card ${report.severity==='warn'?'warning':''}"><div class="collision-card-top"><span class="collision-icon">${icon(report.kind==='duplication'?'mesh':'alert')}</span><span class="collision-kind">${kindName(report.kind)}</span><span class="severity-tag">${report.severity==='block'?'BLOCKING':'WARNING'}</span></div><h3>${escape(report.symbol_id)}</h3><p>${collisionDescription(report)}</p><div class="card-bottom"><div class="participants">${report.participants.map(id=>`${avatar(id)}<span>${escape(name(id))}</span>`).join('')}</div><button class="detail-link" data-report="${index}">Explore conflict ${icon('arrow')}</button></div></article>`;
    }).join(''):`<div class="empty-state">${state.data.collisions.length?'No '+(state.filter==='block'?'blocking conflicts':'warnings')+' in this view.':'No collisions detected. Your team has room to move.'}</div>`;
  }
  function renderContracts() {
    const rows=state.data.nodes.filter(n=>`${n.id} ${n.signature}`.toLowerCase().includes(state.search));
    $('contract-rows').innerHTML=rows.length?rows.map(node=>`<tr><td><button data-symbol="${escape(node.id)}">${escape(node.id)}</button></td><td>${escape(node.signature)}</td><td>${escape(node.owners.map(name).join(', ')||'Main branch')}</td><td><span class="small-badge">${node.collision?'REVIEW':node.owners.length?'WIP':'BASE'}</span></td></tr>`).join(''):'<tr><td colspan="4">No contracts published in this view yet.</td></tr>';
  }
  function showSymbol(id, report=null) {
    const node=state.data.nodes.find(n=>n.id===id);
    if (!node&&!report) {notify('This intent has not published a symbol yet.');return;}
    state.selected={id,signature:node?.signature||report?.sig_after||report?.sig_before||''};
    const reports=report?[report]:state.data.collisions.filter(r=>r.symbol_id===id||r.caller_symbol_id===id);
    $('contract-detail').innerHTML=`<h2 class="detail-title">${escape(id)}</h2><p class="detail-path">${escape(node?.path||'Declared intent · awaiting source')}</p><div class="detail-label">Published signature</div><pre class="contract-code">${escape(state.selected.signature||'No contract published yet')}</pre>${node?.versions.length>1?`<div class="detail-label">Contract versions</div>${node.versions.map(v=>`<p class="detail-path">${escape(v.layer)}</p><pre class="contract-code">${escape(v.signature)}</pre>`).join('')}`:''}${reports.map(r=>`<div class="detail-label">${escape(kindName(r.kind))} · ${escape(r.severity==='block'?'Blocking':'Warning')}</div><p class="detail-message">${escape(r.message)}</p>${r.sig_before?`<div class="detail-label">Before</div><pre class="contract-code">${escape(r.sig_before)}</pre><div class="detail-label">After</div><pre class="contract-code">${escape(r.sig_after||'(deleted)')}</pre>`:''}<div class="detail-label">Suggested next steps</div><div class="detail-resolutions">${r.resolutions.map(v=>`<span class="resolution">${escape(v.replaceAll('_',' '))}</span>`).join('')}</div>`).join('')}`;
    $('copy-contract').disabled=!state.selected.signature;
    if (!$('contract-dialog').open) $('contract-dialog').showModal();
  }
  function view(next) {
    state.view=next;
    document.querySelectorAll('[data-view]').forEach(button=>{button.classList.toggle('active',button.dataset.view===next); button.setAttribute('aria-current',button.dataset.view===next?'page':'false');});
    $('view-label').textContent={overview:'Overview',graph:'Code graph',activity:'Team activity',contracts:'Contracts',collisions:'Collisions'}[next];
    document.body.classList.toggle('graph-focus',next==='graph');document.body.classList.toggle('activity-focus',next==='activity');document.body.classList.toggle('collision-focus',next==='collisions');
    document.querySelector('.content-grid').hidden=['contracts','collisions'].includes(next);
    $('graph-panel').hidden=next==='activity';
    $('contracts-panel').hidden=next!=='contracts';
    $('collision-section').hidden=['contracts','graph','activity'].includes(next);
    if(next==='activity') document.querySelector('.content-grid').style.gridTemplateColumns='1fr';
    else document.querySelector('.content-grid').style.gridTemplateColumns='';
  }
  function switchMode(mode) {
    state.mode=mode; localStorage.setItem('grokmesh-mode',mode);
    $('demo-mode').classList.toggle('selected',mode==='demo');$('demo-mode').setAttribute('aria-pressed',mode==='demo');
    $('live-mode').classList.toggle('selected',mode==='live');$('live-mode').setAttribute('aria-pressed',mode==='live');
    connection('Refreshing workspace…'); clearTimeout(timer); load();
  }
  $('demo-mode').onclick=()=>switchMode('demo');$('live-mode').onclick=()=>switchMode('live');
  $('symbol-search').oninput=event=>{state.search=event.target.value.trim().toLowerCase();if(state.data){renderGraph();renderContracts();}};
  $('zoom-in').onclick=()=>{state.zoom=Math.min(1.8,state.zoom+.15);zoom();};
  $('zoom-out').onclick=()=>{state.zoom=Math.max(.55,state.zoom-.15);zoom();};
  $('zoom-reset').onclick=()=>{state.zoom=1;zoom();};
  $('present-button').onclick=()=>{const active=document.body.classList.toggle('presentation');$('present-button').querySelector('span').textContent=active?'Exit presentation':'Present';$('present-button').setAttribute('aria-pressed',active);};
  $('close-dialog').onclick=$('dismiss-dialog').onclick=()=>$('contract-dialog').close();
  $('contract-dialog').onclick=event=>{if(event.target===$('contract-dialog')){const r=event.target.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)event.target.close();}};
  $('copy-contract').onclick=async()=>{try{await navigator.clipboard.writeText(state.selected.signature);notify('Contract copied to clipboard');}catch{notify('Copy unavailable. Select the signature text to copy it.');}};
  document.addEventListener('click',event=>{
    const target=event.target.closest('[data-symbol], [data-report], [data-view], [data-filter]');if(!target||!state.data)return;
    if(target.dataset.symbol)showSymbol(target.dataset.symbol);
    if(target.dataset.report!==undefined){const report=state.data.collisions[Number(target.dataset.report)];showSymbol(report.symbol_id,report);}
    if(target.dataset.view)view(target.dataset.view);
    if(target.dataset.filter){state.filter=target.dataset.filter;document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('selected',b===target));renderCollisions();}
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)&&!$('contract-dialog').open){event.preventDefault();view('graph');$('symbol-search').focus();}
    if((event.key==='Enter'||event.key===' ')&&event.target.classList.contains('graph-node')){event.preventDefault();showSymbol(event.target.dataset.symbol);}
    if(event.key==='Escape'&&document.body.classList.contains('presentation')&&!$('contract-dialog').open)$('present-button').click();
  });
  switchMode(state.mode==='live'?'live':'demo');
})();
