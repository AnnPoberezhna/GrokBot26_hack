import React from 'react';
import {
	AbsoluteFill,
	interpolate,
	OffthreadVideo,
	spring,
	staticFile,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';
import {Backdrop, useRise} from './Backdrop';
import demoLines from './demoLines.json';
import {C, mono, sans} from './theme';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const Kicker: React.FC<{children: React.ReactNode; delay?: number; color?: string}> = ({
	children,
	delay = 0,
	color = C.mute,
}) => (
	<div
		style={{
			...useRise(delay),
			fontFamily: mono,
			fontSize: 22,
			letterSpacing: 6,
			textTransform: 'uppercase',
			color,
		}}
	>
		{children}
	</div>
);

/* 1 ─ Cold open */
export const ColdOpen: React.FC = () => (
	<AbsoluteFill>
		<Backdrop />
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', gap: 28}}>
			<div style={{...useRise(8, 24), fontFamily: sans, fontSize: 84, fontWeight: 700, color: C.text}}>
				Every developer has an AI agent.
			</div>
			<div style={{...useRise(55, 24), fontFamily: sans, fontSize: 84, fontWeight: 700, color: C.mute}}>
				Every agent works <span style={{color: C.block}}>alone.</span>
			</div>
		</AbsoluteFill>
	</AbsoluteFill>
);

/* 2 ─ Problem: two lanes drift, collide at the pull request */
const laneA = [
	'def issue(user_id, ttl_s):',
	'    exp = now() + ttl_s',
	'    return sign(user_id, exp)',
	'def hash_token(t): ...',
];
const laneB = [
	'def issue(user_id) -> str:',
	'    key = rotate_key()',
	'    return sign_v2(user_id, key)',
	'def hash_token(t): ...   # again',
];

const Lane: React.FC<{who: string; color: string; lines: string[]; delay: number}> = ({
	who,
	color,
	lines,
	delay,
}) => {
	const f = useCurrentFrame();
	return (
		<div
			style={{
				...useRise(delay),
				width: 700,
				padding: '28px 34px',
				borderRadius: 18,
				background: `${C.panel}ee`,
				border: `1px solid ${color}55`,
				boxShadow: `0 0 60px ${color}18`,
			}}
		>
			<div style={{fontFamily: mono, fontSize: 20, color, letterSpacing: 3, marginBottom: 18}}>
				● {who}
			</div>
			{lines.map((line, i) => {
				const start = delay + 20 + i * 22;
				const chars = Math.floor(interpolate(f, [start, start + 18], [0, line.length], clamp));
				return (
					<div key={i} style={{fontFamily: mono, fontSize: 26, color: C.text, height: 40, whiteSpace: 'pre'}}>
						{line.slice(0, chars)}
					</div>
				);
			})}
		</div>
	);
};

export const Problem: React.FC = () => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const merge = spring({frame: f - 175, fps, config: {damping: 14, mass: 0.8}});
	const shake = f > 190 && f < 215 ? Math.sin(f * 2.4) * 10 * (1 - (f - 190) / 25) : 0;
	const flash = interpolate(f, [188, 194, 225], [0, 0.22, 0], clamp);
	return (
		<AbsoluteFill>
			<Backdrop glow={C.block} glow2={C.marcel} />
			<AbsoluteFill style={{alignItems: 'center', paddingTop: 90}}>
				<Kicker>Agents write code in minutes</Kicker>
			</AbsoluteFill>
			<AbsoluteFill
				style={{
					justifyContent: 'center',
					alignItems: 'center',
					flexDirection: 'row',
					gap: interpolate(merge, [0, 1], [120, -40]),
					transform: `translateX(${shake}px) scale(${interpolate(merge, [0, 1], [1, 0.92])})`,
				}}
			>
				<Lane who="Anna's agent" color={C.anna} lines={laneA} delay={10} />
				<Lane who="Marcel's agent" color={C.marcel} lines={laneB} delay={22} />
			</AbsoluteFill>
			<AbsoluteFill style={{backgroundColor: C.block, opacity: flash}} />
			<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 110}}>
				<div
					style={{
						...useRise(195, 16),
						fontFamily: sans,
						fontSize: 56,
						fontWeight: 800,
						color: C.text,
					}}
				>
					Teams find the collision at the <span style={{color: C.block}}>pull request.</span>
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

/* 3 ─ Title */
export const Title: React.FC = () => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const s = spring({frame: f - 6, fps, config: {damping: 18}});
	return (
		<AbsoluteFill>
			<Backdrop glow={C.violet} glow2={C.anna} />
			<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', gap: 30}}>
				<div
					style={{
						fontFamily: sans,
						fontWeight: 800,
						fontSize: 190,
						letterSpacing: interpolate(s, [0, 1], [40, -4]),
						opacity: s,
						backgroundImage: `linear-gradient(100deg, ${C.anna}, ${C.violet} 55%, ${C.marcel})`,
						WebkitBackgroundClip: 'text',
						color: 'transparent',
						filter: `drop-shadow(0 0 ${interpolate(s, [0, 1], [0, 40])}px ${C.violet}66)`,
					}}
				>
					GrokMesh
				</div>
				<div style={{...useRise(30), fontFamily: sans, fontSize: 44, color: C.text, fontWeight: 500}}>
					One live code graph for every coding agent on the team.
				</div>
				<Kicker delay={50} color={C.mute}>
					Sync at intent · not at the pull request
				</Kicker>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

/* 4 ─ How it works: the symbol graph */
type Node = {id: string; label: string; x: number; y: number};
const nodes: Node[] = [
	{id: 'issue', label: 'auth.issue()', x: 760, y: 380},
	{id: 'verify', label: 'auth.verify()', x: 760, y: 700},
	{id: 'login', label: 'api.login()', x: 1220, y: 380},
	{id: 'me', label: 'api.me()', x: 1220, y: 700},
];
const at = (id: string) => nodes.find((n) => n.id === id)!;

export const Graph: React.FC = () => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const steps = ['Declare intent', 'Check the live graph', 'Block · reuse · adapt'];
	const stepAt = [10, 80, 150];
	const anna = interpolate(f, [40, 60], [0, 1], clamp);
	const travel = interpolate(f, [95, 140], [0, 1], {...clamp, easing: (t) => 1 - Math.pow(1 - t, 3)});
	const hit = spring({frame: f - 140, fps, config: {damping: 9}});
	const broken = interpolate(f, [195, 215], [0, 1], clamp);
	const issue = at('issue');
	const login = at('login');
	const mStart = {x: 300, y: 380};
	const mx = mStart.x + (issue.x - 110 - mStart.x) * travel;
	return (
		<AbsoluteFill>
			<Backdrop glow={C.anna} glow2={C.violet} />
			<AbsoluteFill style={{flexDirection: 'row', justifyContent: 'center', alignItems: 'flex-start', gap: 40, paddingTop: 70}}>
				{steps.map((s, i) => {
					const on = f >= stepAt[i];
					return (
						<div
							key={s}
							style={{
								...useRise(stepAt[i] - 6, 14),
								fontFamily: sans,
								fontSize: 30,
								fontWeight: 700,
								color: on ? C.text : C.faint,
								padding: '14px 26px',
								borderRadius: 999,
								border: `1px solid ${on ? C.violet : C.panelEdge}`,
								background: on ? `${C.violet}22` : 'transparent',
							}}
						>
							<span style={{color: C.violet, marginRight: 12, fontFamily: mono}}>{i + 1}</span>
							{s}
						</div>
					);
				})}
			</AbsoluteFill>
			<svg width={1920} height={1080} style={{position: 'absolute'}}>
				{[
					['login', 'issue'],
					['me', 'verify'],
				].map(([a, b]) => {
					const p = at(a);
					const q = at(b);
					const red = a === 'login' ? broken : 0;
					return (
						<g key={a}>
							<line
								x1={p.x - 110}
								y1={p.y}
								x2={q.x + 110}
								y2={q.y}
								stroke={red > 0 ? C.block : C.faint}
								strokeWidth={3 + red * 3}
								strokeDasharray="10 10"
								strokeDashoffset={-f * 1.5}
							/>
							<text
								x={(p.x + q.x) / 2}
								y={p.y - 18}
								fill={red > 0 ? C.block : C.mute}
								fontFamily={mono}
								fontSize={20}
								textAnchor="middle"
							>
								{red > 0 ? 'broken contract' : 'calls'}
							</text>
						</g>
					);
				})}
			</svg>
			{nodes.map((n) => {
				const isIssue = n.id === 'issue';
				const isLogin = n.id === 'login';
				const ring = isIssue ? anna : 0;
				const glow = isIssue ? C.anna : isLogin && broken > 0 ? C.block : C.panelEdge;
				return (
					<div
						key={n.id}
						style={{
							position: 'absolute',
							left: n.x - 110,
							top: n.y - 42,
							width: 220,
							height: 84,
							borderRadius: 16,
							display: 'flex',
							alignItems: 'center',
							justifyContent: 'center',
							fontFamily: mono,
							fontSize: 24,
							color: C.text,
							background: C.panel,
							border: `2px solid ${ring > 0 || (isLogin && broken > 0) ? glow : C.panelEdge}`,
							boxShadow: `0 0 ${40 * Math.max(ring, isLogin ? broken : 0)}px ${glow}88`,
						}}
					>
						{n.label}
					</div>
				);
			})}
			<div
				style={{
					position: 'absolute',
					left: issue.x - 110,
					top: issue.y - 100,
					width: 220,
					textAlign: 'center',
					fontFamily: mono,
					fontSize: 20,
					color: C.anna,
					opacity: anna,
				}}
			>
				anna · lease
			</div>
			<div
				style={{
					position: 'absolute',
					left: mx - 150,
					top: mStart.y - 30,
					width: 150,
					height: 60,
					borderRadius: 999,
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'center',
					fontFamily: mono,
					fontSize: 22,
					color: C.bg,
					fontWeight: 700,
					background: C.marcel,
					opacity: interpolate(f, [80, 95], [0, 1], clamp),
					transform: `translateX(${-hit * 30}px)`,
				}}
			>
				marcel
			</div>
			<div
				style={{
					position: 'absolute',
					left: issue.x - 330,
					top: issue.y + 60,
					fontFamily: sans,
					fontWeight: 800,
					fontSize: 44,
					color: C.block,
					opacity: hit,
					transform: `scale(${0.8 + hit * 0.2})`,
				}}
			>
				BLOCKED
			</div>
			<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 90}}>
				<div style={{...useRise(200), fontFamily: sans, fontSize: 40, color: C.text, fontWeight: 500}}>
					Leases on symbols · signatures · call edges, updated from every agent's work in progress
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

/* 5 ─ Demo: real output of demo/run_demo.py, or a screen recording if present */
type Line = {text: string; tone: string};
const toneColor: Record<string, string> = {
	title: C.ok,
	step: C.anna,
	call: C.text,
	ok: C.ok,
	block: C.block,
	warn: C.marcel,
	dim: C.mute,
	plain: C.text,
};

const schedule = (() => {
	let t = 24;
	return (demoLines as Line[]).map((l) => {
		if (l.tone === 'step') t += 16;
		const start = t;
		t += l.text === '' ? 4 : l.tone === 'call' ? 16 : 11;
		return start;
	});
})();

export const DEMO_CLIP: string | null = null; // e.g. 'two-agents.mp4' in pitch/public/

export const Demo: React.FC = () => {
	const f = useCurrentFrame();
	const lines = demoLines as Line[];
	const maxRows = 22;
	const scrollY =
		lines.reduce(
			(acc, _, i) =>
				i < maxRows ? acc : acc + interpolate(f, [schedule[i], schedule[i] + 8], [0, 1], clamp),
			0,
		) * 34;
	if (DEMO_CLIP) {
		return (
			<AbsoluteFill>
				<Backdrop />
				<OffthreadVideo src={staticFile(DEMO_CLIP)} style={{width: '100%', height: '100%'}} />
			</AbsoluteFill>
		);
	}
	return (
		<AbsoluteFill>
			<Backdrop glow={C.violet} glow2={C.block} />
			<AbsoluteFill style={{alignItems: 'center', paddingTop: 50}}>
				<Kicker color={C.mute}>Live demo · two agents · one broker</Kicker>
			</AbsoluteFill>
			<div
				style={{
					...useRise(0, 14),
					position: 'absolute',
					left: 150,
					top: 120,
					width: 1620,
					height: 880,
					borderRadius: 20,
					background: `${C.panel}f2`,
					border: `1px solid ${C.panelEdge}`,
					boxShadow: `0 40px 120px rgba(0,0,0,0.6), 0 0 80px ${C.violet}14`,
					overflow: 'hidden',
				}}
			>
				<div
					style={{
						height: 54,
						display: 'flex',
						alignItems: 'center',
						gap: 10,
						padding: '0 22px',
						borderBottom: `1px solid ${C.panelEdge}`,
					}}
				>
					{[C.block, C.marcel, C.ok].map((c) => (
						<div key={c} style={{width: 14, height: 14, borderRadius: 7, background: c, opacity: 0.8}} />
					))}
					<div style={{fontFamily: mono, fontSize: 18, color: C.mute, marginLeft: 18}}>
						uv run python demo/run_demo.py
					</div>
				</div>
				<div style={{height: 880 - 55, overflow: 'hidden'}}>
				<div style={{padding: '22px 34px', transform: `translateY(${-scrollY}px)`}}>
					{lines.map((l, i) => {
						if (f < schedule[i]) return null;
						const typed =
							l.tone === 'call'
								? Math.floor(interpolate(f, [schedule[i], schedule[i] + 12], [0, l.text.length], clamp))
								: l.text.length;
						const pop = interpolate(f, [schedule[i], schedule[i] + 8], [0, 1], clamp);
						const isBlock = l.tone === 'block';
						return (
							<div
								key={i}
								style={{
									fontFamily: mono,
									fontSize: 24,
									lineHeight: '34px',
									height: 34,
									whiteSpace: 'pre',
									color: toneColor[l.tone] ?? C.text,
									fontWeight: l.tone === 'step' || l.tone === 'title' || isBlock ? 700 : 400,
									opacity: l.tone === 'call' ? 1 : pop,
									textShadow: isBlock ? `0 0 18px ${C.block}aa` : 'none',
									background: isBlock ? `${C.block}${Math.round(pop * 20).toString(16).padStart(2, '0')}` : 'none',
								}}
							>
								{l.text.slice(0, typed)}
							</div>
						);
					})}
				</div>
				</div>
			</div>
		</AbsoluteFill>
	);
};

export const DEMO_FRAMES = schedule[schedule.length - 1] + 75;

/* 6 ─ Outcome */
const cards = [
	{title: 'Same symbol', body: 'Two agents claim one function. The second is blocked before it writes code.', color: C.anna},
	{title: 'Broken contract', body: 'A signature changes. Callers in other agents’ work are flagged through the call graph.', color: C.block},
	{title: 'Mesh Bot', body: 'One shared view: who works on what, and every open collision.', color: C.marcel},
];

export const Outcome: React.FC = () => (
	<AbsoluteFill>
		<Backdrop glow={C.violet} glow2={C.ok} />
		<AbsoluteFill style={{alignItems: 'center', paddingTop: 140}}>
			<Kicker>Caught at intent time</Kicker>
		</AbsoluteFill>
		<AbsoluteFill style={{flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 40}}>
			{cards.map((c, i) => (
				<div
					key={c.title}
					style={{
						...useRise(10 + i * 14, 20),
						width: 500,
						minHeight: 360,
						padding: 44,
						borderRadius: 24,
						background: `${C.panel}ee`,
						border: `1px solid ${c.color}55`,
						boxShadow: `0 0 70px ${c.color}14`,
						display: 'flex',
						flexDirection: 'column',
						gap: 24,
					}}
				>
					<div style={{width: 56, height: 6, flexShrink: 0, borderRadius: 3, background: c.color}} />
					<div style={{fontFamily: sans, fontSize: 46, fontWeight: 800, color: C.text}}>{c.title}</div>
					<div style={{fontFamily: sans, fontSize: 30, lineHeight: 1.4, color: C.mute}}>{c.body}</div>
				</div>
			))}
		</AbsoluteFill>
	</AbsoluteFill>
);

/* 7 ─ Close */
export const Close: React.FC = () => (
	<AbsoluteFill>
		<Backdrop glow={C.violet} glow2={C.anna} />
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', gap: 34}}>
			<div style={{...useRise(6, 22), fontFamily: sans, fontSize: 92, fontWeight: 800, color: C.text}}>
				Sync at <span style={{color: C.anna}}>intent</span>, not at the pull request.
			</div>
			<div style={{...useRise(30), fontFamily: mono, fontSize: 30, color: C.mute}}>
				GrokMesh · MCP server for Grok Bots
			</div>
			<div style={{...useRise(50), fontFamily: sans, fontSize: 28, color: C.faint, marginTop: 30}}>
				Anna Poberezhna · Tsimur Halkin · Marcel Musiałek
			</div>
		</AbsoluteFill>
	</AbsoluteFill>
);
