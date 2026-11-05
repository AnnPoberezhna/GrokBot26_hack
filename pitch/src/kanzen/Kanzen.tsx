/**
 * GrokMesh pitch film in the Kanzen design system (light theme).
 * Bone and graphite, one red spent once per slide, square corners,
 * one 45-degree notch per slab, hairlines instead of boxes. No glow, no gradient.
 */
import React from 'react';
import {loadFont as loadChakra} from '@remotion/google-fonts/ChakraPetch';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadMono} from '@remotion/google-fonts/JetBrainsMono';
import {linearTiming, TransitionSeries} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import demoLines from '../demoLines.json';

const display = loadChakra('normal', {weights: ['600', '700'], subsets: ['latin', 'latin-ext']})
	.fontFamily;
const sans = loadInter('normal', {weights: ['400', '500'], subsets: ['latin', 'latin-ext']}).fontFamily;
const mono = loadMono('normal', {weights: ['400', '500', '700'], subsets: ['latin', 'latin-ext']})
	.fontFamily;

/* Kanzen tokens, light theme. */
const K = {
	base: '#F7F7F5',
	raised: '#FFFFFF',
	sunken: '#EDEDEA',
	ink: '#121316',
	muted: '#5C5E61',
	faint: '#8C8E92',
	accent: '#C8102E',
	accentInk: '#FFFFFF',
	hairline: '#DFDFDA',
	grid: '#E7E7E3',
};
/* Slide scale: Kanzen sizes ×1.75 for a 1920×1080 frame. Spacing stays on the 4px base. */
const S = {eyebrow: 23, title: 78, section: 120, lead: 38, body: 31, caption: 25, metric: 30, code: 26};
const NOTCH = 24;
const MARGIN = 112;

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ease = Easing.bezier(0.2, 0, 0, 1);

const useIn = (start: number, dur = 16) => {
	const f = useCurrentFrame();
	return interpolate(f, [start, start + dur], [0, 1], {...clamp, easing: ease});
};

const Reveal: React.FC<{at: number; children: React.ReactNode; style?: React.CSSProperties}> = ({
	at,
	children,
	style,
}) => {
	const t = useIn(at);
	return <div style={{opacity: t, transform: `translateY(${(1 - t) * 12}px)`, ...style}}>{children}</div>;
};

/** A hairline that draws from left to right. */
const Rule: React.FC<{at: number; width: number | string; color?: string; style?: React.CSSProperties}> = ({
	at,
	width,
	color = K.hairline,
	style,
}) => {
	const t = useIn(at, 20);
	return (
		<div
			style={{
				width,
				height: 2,
				background: color,
				transform: `scaleX(${t})`,
				transformOrigin: 'left',
				...style,
			}}
		/>
	);
};

const notchPath = (n: number) =>
	`polygon(0 0, calc(100% - ${n}px) 0, 100% ${n}px, 100% 100%, 0 100%)`;

/** A raised slab with a 1px hairline edge and one bevelled corner (top right). */
const Slab: React.FC<{
	at: number;
	children: React.ReactNode;
	style?: React.CSSProperties;
	edge?: string;
	fill?: string;
	notch?: boolean;
}> = ({at, children, style, edge = K.hairline, fill = K.raised, notch = true}) => {
	const t = useIn(at, 18);
	const clip = notch ? notchPath(NOTCH) : undefined;
	return (
		<div
			style={{
				background: edge,
				clipPath: clip,
				padding: 2,
				opacity: t,
				transform: `translateY(${(1 - t) * 16}px)`,
				...style,
			}}
		>
			<div style={{background: fill, clipPath: notch ? notchPath(NOTCH - 1) : undefined, height: '100%'}}>
				{children}
			</div>
		</div>
	);
};

const Eyebrow: React.FC<{children: React.ReactNode; at?: number}> = ({children, at = 0}) => (
	<Reveal at={at}>
		<div
			style={{
				fontFamily: display,
				fontWeight: 600,
				fontSize: S.eyebrow,
				letterSpacing: '0.16em',
				textTransform: 'uppercase',
				color: K.muted,
			}}
		>
			{children}
		</div>
	</Reveal>
);

const Title: React.FC<{children: React.ReactNode; at?: number; size?: number}> = ({
	children,
	at = 6,
	size = S.title,
}) => (
	<Reveal at={at}>
		<div
			style={{
				fontFamily: display,
				fontWeight: size >= S.section ? 700 : 600,
				fontSize: size,
				lineHeight: 1.05,
				letterSpacing: size >= S.section ? '-0.02em' : '-0.01em',
				color: K.ink,
			}}
		>
			{children}
		</div>
	</Reveal>
);

const Lead: React.FC<{children: React.ReactNode; at: number; color?: string; style?: React.CSSProperties}> = ({
	children,
	at,
	color = K.muted,
	style,
}) => (
	<Reveal at={at}>
		<div style={{fontFamily: sans, fontSize: S.lead, lineHeight: 1.45, color, maxWidth: 1400, ...style}}>
			{children}
		</div>
	</Reveal>
);

const Mono: React.FC<{children: React.ReactNode; size?: number; color?: string; weight?: number}> = ({
	children,
	size = S.code,
	color = K.ink,
	weight = 400,
}) => <span style={{fontFamily: mono, fontSize: size, color, fontWeight: weight, whiteSpace: 'pre'}}>{children}</span>;

const Red: React.FC<{children: React.ReactNode}> = ({children}) => (
	<span style={{color: K.accent}}>{children}</span>
);

/** Slide chrome: ground, plus-grid, footer rule with name and slide number. */
const Slide: React.FC<{n: number; total: number; children: React.ReactNode}> = ({n, total, children}) => (
	<AbsoluteFill style={{background: K.base}}>
		<svg width="1920" height="1080" style={{position: 'absolute'}}>
			<defs>
				<pattern id="plus" width="48" height="48" patternUnits="userSpaceOnUse">
					<path d="M24 19 V29 M19 24 H29" stroke={K.grid} strokeWidth="2" />
				</pattern>
			</defs>
			<rect width="1920" height="1080" fill="url(#plus)" />
		</svg>
		<div style={{position: 'absolute', left: MARGIN, right: MARGIN, top: MARGIN, bottom: 150}}>
			{children}
		</div>
		<div
			style={{
				position: 'absolute',
				left: MARGIN,
				right: MARGIN,
				bottom: 72,
				borderTop: `2px solid ${K.hairline}`,
				paddingTop: 20,
				display: 'flex',
				justifyContent: 'space-between',
				fontFamily: display,
				fontWeight: 600,
				fontSize: 20,
				letterSpacing: '0.16em',
				textTransform: 'uppercase',
				color: K.faint,
			}}
		>
			<span>GrokMesh</span>
			<span style={{fontFamily: mono, letterSpacing: 0}}>
				{String(n).padStart(2, '0')} / {String(total).padStart(2, '0')}
			</span>
		</div>
	</AbsoluteFill>
);

const TOTAL = 8;

/* 01 — Opening */
const Opening: React.FC = () => (
	<Slide n={1} total={TOTAL}>
		<div style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%', gap: 36}}>
			<Eyebrow>Grok Bot Hackathon · Wrocław</Eyebrow>
			<Title size={104} at={8}>
				Every developer has an AI agent.
			</Title>
			<Title size={104} at={40}>
				<span style={{color: K.muted}}>Every agent codes </span>
				<Red>alone.</Red>
			</Title>
		</div>
	</Slide>
);

/* Timeline used by 02 and 03. */
const AXIS_L = 330;
const AXIS_R = 1560;
const Lanes: React.FC<{at: number}> = ({at}) => {
	const f = useCurrentFrame();
	const lanes = [
		{who: 'anna · agent', y: 120, blocks: ['declare: token expiry', 'issue(user_id, ttl_s)', 'hash_token()']},
		{who: 'marcel · agent', y: 250, blocks: ['rewrite signing', 'issue() → new keys', 'hash_token()  again']},
	];
	return (
		<>
			{lanes.map((lane, li) => (
				<React.Fragment key={lane.who}>
					<div style={{position: 'absolute', left: 0, top: lane.y + 30}}>
						<Reveal at={at + li * 6}>
							<Mono size={24} color={K.muted}>
								{lane.who}
							</Mono>
						</Reveal>
					</div>
					{lane.blocks.map((b, bi) => {
						const start = at + 20 + bi * 26 + li * 10;
						const w = interpolate(f, [start, start + 22], [0, 340], {...clamp, easing: ease});
						return (
							<div
								key={b}
								style={{
									position: 'absolute',
									left: AXIS_L + bi * 380,
									top: lane.y,
									width: w,
									height: 96,
									overflow: 'hidden',
									background: K.raised,
									borderTop: `2px solid ${K.ink}`,
									borderBottom: `2px solid ${K.hairline}`,
									display: 'flex',
									alignItems: 'center',
									paddingLeft: w > 40 ? 22 : 0,
								}}
							>
								<Mono size={24}>{b}</Mono>
							</div>
						);
					})}
				</React.Fragment>
			))}
			<div style={{position: 'absolute', left: AXIS_L, top: 400}}>
				<Rule at={at} width={AXIS_R - AXIS_L} color={K.ink} />
			</div>
			{['18:00', '19:00', '20:00', '21:00'].map((t, i) => (
				<div key={t} style={{position: 'absolute', left: AXIS_L + i * 400 - 30, top: 416}}>
					<Reveal at={at + 10}>
						<Mono size={20} color={K.faint}>
							{t}
						</Mono>
					</Reveal>
				</div>
			))}
		</>
	);
};

const Marker: React.FC<{x: number; label: string; sub: string; at: number}> = ({x, label, sub, at}) => {
	const t = useIn(at, 14);
	return (
		<div style={{position: 'absolute', left: x, top: 90, opacity: t}}>
			<div style={{width: 4, height: 320, background: K.accent, transform: `scaleY(${t})`, transformOrigin: 'top'}} />
			<div style={{position: 'absolute', top: 302, left: -8, width: 20, height: 20, background: K.accent}} />
			<div style={{position: 'absolute', top: -58, ...(x > 1200 ? {right: -2, textAlign: 'right'} : {left: -2}), whiteSpace: 'nowrap'}}>
				<Mono size={24} color={K.accent} weight={700}>
					{label}
				</Mono>
			</div>
			<div style={{position: 'absolute', top: -26, ...(x > 1200 ? {right: -2, textAlign: 'right'} : {left: -2}), whiteSpace: 'nowrap'}}>
				<span style={{fontFamily: sans, fontSize: 22, color: K.muted}}>{sub}</span>
			</div>
		</div>
	);
};

/* 02 — Where it breaks today */
const Problem: React.FC = () => (
	<Slide n={2} total={TOTAL}>
		<Eyebrow>02 — Where it breaks today</Eyebrow>
		<div style={{position: 'absolute', left: 0, right: 0, top: 60, height: 560}}>
			<Lanes at={8} />
			<Marker x={AXIS_R} label="PULL REQUEST" sub="conflict found here" at={150} />
		</div>
		<div style={{position: 'absolute', left: 0, bottom: 0}}>
			<Lead at={175} color={K.ink}>
				Both agents wrote the code. Git compares lines after the fact.
			</Lead>
			<Lead at={195}>Two hours of agent work collide at merge.</Lead>
		</div>
	</Slide>
);

/* 03 — The idea */
const Shift: React.FC = () => {
	const f = useCurrentFrame();
	const x = interpolate(f, [40, 95], [AXIS_R, AXIS_L - 20], {...clamp, easing: ease});
	return (
		<Slide n={3} total={TOTAL}>
			<Eyebrow>03 — The idea</Eyebrow>
			<div style={{position: 'absolute', left: 0, right: 0, top: 60, height: 560}}>
				<Lanes at={-200} />
				<Marker x={x} label={f < 95 ? 'PULL REQUEST' : 'INTENT'} sub={f < 95 ? 'today' : 'GrokMesh checks here'} at={-20} />
			</div>
			<div style={{position: 'absolute', left: 0, bottom: 0}}>
				<Title at={100} size={62}>
					Move the check from the pull request to the intent.
				</Title>
				<Lead at={125} style={{marginTop: 20}}>
					Before an agent writes a line, it says what it will change. The broker answers.
				</Lead>
			</div>
		</Slide>
	);
};

/* 04 — How it works */
const Arrow: React.FC<{at: number; left: number; top: number}> = ({at, left, top}) => {
	const t = useIn(at, 14);
	return (
		<div style={{position: 'absolute', left, top, display: 'flex', alignItems: 'center', opacity: t}}>
			<div style={{width: 56 * t, height: 2, background: K.ink}} />
			<div
				style={{
					width: 0,
					height: 0,
					borderTop: '9px solid transparent',
					borderBottom: '9px solid transparent',
					borderLeft: `14px solid ${K.ink}`,
				}}
			/>
		</div>
	);
};

const ColHead: React.FC<{n: string; title: string; sub: string}> = ({n, title, sub}) => (
	<div style={{padding: '28px 30px 18px', borderBottom: `2px solid ${K.hairline}`}}>
		<div style={{display: 'flex', gap: 14, alignItems: 'baseline'}}>
			<Mono size={22} color={K.faint}>
				{n}
			</Mono>
			<span style={{fontFamily: display, fontWeight: 600, fontSize: 38, color: K.ink}}>{title}</span>
		</div>
		<div style={{fontFamily: sans, fontSize: 22, color: K.muted, marginTop: 8}}>{sub}</div>
	</div>
);

const Row: React.FC<{at: number; children: React.ReactNode; last?: boolean}> = ({at, children, last}) => (
	<Reveal at={at}>
		<div style={{padding: '16px 30px', borderBottom: last ? 'none' : `2px solid ${K.hairline}`}}>{children}</div>
	</Reveal>
);

const RowText: React.FC<{head: string; body: string}> = ({head, body}) => (
	<>
		<div style={{fontFamily: mono, fontSize: 23, color: K.ink, fontWeight: 500}}>{head}</div>
		<div style={{fontFamily: sans, fontSize: 21, color: K.muted, marginTop: 4}}>{body}</div>
	</>
);

const How: React.FC = () => {
	const colW = 500;
	const gap = 98;
	const verdict = useIn(370, 14);
	return (
		<Slide n={4} total={TOTAL}>
			<Eyebrow>04 — How it works</Eyebrow>
			<div style={{position: 'absolute', left: 0, top: 70, display: 'flex', gap}}>
				<Slab at={10} style={{width: colW, height: 640}}>
					<ColHead n="A" title="Agents" sub="Each Grok Bot calls the broker over MCP." />
					<Row at={30}>
						<RowText head="declare_intent()" body="symbols it will produce or modify" />
					</Row>
					<Row at={42}>
						<RowText head="sync_file()" body="the changed file, after each edit" />
					</Row>
					<Row at={54}>
						<RowText head="get_contracts()" body="current signatures before it calls them" />
					</Row>
					<Row at={66} last>
						<RowText head="get_activity()" body="Mesh Bot: who works on what" />
					</Row>
				</Slab>
				<Slab at={110} style={{width: colW, height: 640}}>
					<ColHead n="B" title="Live code graph" sub="Symbols, signatures, call edges. No source kept." />
					<Row at={130}>
						<RowText head="base" body="main branch, parsed at start" />
					</Row>
					<Row at={142}>
						<RowText head="overlay · anna" body="her uncommitted symbols" />
					</Row>
					<Row at={154}>
						<RowText head="overlay · marcel" body="his uncommitted symbols" />
					</Row>
					<Row at={166} last>
						<RowText head="leases" body="claims on symbols, 30 min TTL" />
					</Row>
				</Slab>
				<Slab at={220} style={{width: colW, height: 640}}>
					<ColHead n="C" title="Checks" sub="Cheap and exact first. Fuzzy last." />
					<Row at={240}>
						<RowText head="1  same symbol" body="two active claims on one function" />
					</Row>
					<Row at={262}>
						<RowText head="2  broken contract" body="signature diff + a calls edge" />
					</Row>
					<Row at={284}>
						<RowText head="3  duplication" body="BM25 match against other intents" />
					</Row>
					<div
						style={{
							margin: '22px 30px',
							padding: '14px 20px',
							background: K.accent,
							color: K.accentInk,
							fontFamily: mono,
							fontWeight: 700,
							fontSize: 23,
							opacity: verdict,
						}}
					>
						BLOCK / WARN + resolution
					</div>
				</Slab>
			</div>
			<Arrow at={95} left={colW + 18} top={390} />
			<Arrow at={205} left={2 * colW + gap + 18} top={390} />
			<div style={{position: 'absolute', left: 0, bottom: 0}}>
				<Lead at={400}>Stages 1 and 2 can block an edit. Stage 3 only warns.</Lead>
			</div>
		</Slide>
	);
};

/* 05 — The unit is a symbol */
const fields: [string, string, boolean?][] = [
	['signature', 'def issue(user_id: str, ttl_s: int) -> str'],
	['on main', 'def issue(user_id: str) -> str'],
	['change', 'breaking', true],
	['owner', 'anna · lease, 30 min'],
	['called by', 'demo.api.login   (marcel is editing it)'],
];

const Symbol: React.FC = () => (
	<Slide n={5} total={TOTAL}>
		<Eyebrow>05 — The unit is a symbol, not a file</Eyebrow>
		<div style={{position: 'absolute', left: 0, top: 80, width: 1120}}>
			<Slab at={10} style={{width: 1120}}>
				<div
					style={{
						padding: '30px 40px',
						borderBottom: `2px solid ${K.hairline}`,
						display: 'flex',
						justifyContent: 'space-between',
						alignItems: 'baseline',
					}}
				>
					<Mono size={40} weight={700}>
						demo.auth.issue
					</Mono>
					<Mono size={22} color={K.faint}>
						function · demo/auth.py
					</Mono>
				</div>
				{fields.map(([k, v, red], i) => (
					<Reveal key={k} at={30 + i * 18}>
						<div
							style={{
								display: 'flex',
								padding: '20px 40px',
								borderBottom: i === fields.length - 1 ? 'none' : `2px solid ${K.hairline}`,
							}}
						>
							<div style={{width: 230}}>
								<Mono size={24} color={K.muted}>
									{k}
								</Mono>
							</div>
							<Mono size={27} color={red ? K.accent : K.ink} weight={red ? 700 : 400}>
								{v}
							</Mono>
						</div>
					</Reveal>
				))}
			</Slab>
		</div>
		<div style={{position: 'absolute', left: 1200, top: 110, width: 490}}>
			<Lead at={130} color={K.ink} style={{fontSize: 30}}>
				The broker diffs signatures and follows call edges.
			</Lead>
			<Lead at={150} style={{fontSize: 30, marginTop: 24}}>
				That is how a change in one agent&apos;s work reaches another agent&apos;s caller, before either one
				commits.
			</Lead>
		</div>
	</Slide>
);

/* 06 — Live demo: the real output of demo/run_demo.py */
type Line = {text: string; tone: string};
const tone: Record<string, {color: string; weight: number}> = {
	title: {color: K.ink, weight: 700},
	step: {color: K.ink, weight: 700},
	call: {color: K.ink, weight: 400},
	ok: {color: K.muted, weight: 400},
	block: {color: K.accent, weight: 700},
	warn: {color: K.muted, weight: 700},
	dim: {color: K.faint, weight: 400},
	plain: {color: K.ink, weight: 400},
};
const LINES = demoLines as Line[];
const schedule = (() => {
	let t = 30;
	return LINES.map((l) => {
		if (l.tone === 'step') t += 18;
		const s = t;
		t += l.text === '' ? 4 : l.tone === 'call' ? 16 : 11;
		return s;
	});
})();
export const KANZEN_DEMO_FRAMES = schedule[schedule.length - 1] + 80;

const Demo: React.FC = () => {
	const f = useCurrentFrame();
	const rows = 19;
	const lh = 36;
	const scroll =
		LINES.reduce((acc, _, i) => (i < rows ? acc : acc + interpolate(f, [schedule[i], schedule[i] + 8], [0, 1], clamp)), 0) *
		lh;
	return (
		<Slide n={6} total={TOTAL}>
			<Eyebrow>06 — Live demo · two agents, one broker</Eyebrow>
			<Slab at={4} fill={K.sunken} style={{position: 'absolute', left: 0, right: 0, top: 60, height: 760}}>
				<div
					style={{
						padding: '16px 32px',
						borderBottom: `2px solid ${K.hairline}`,
						display: 'flex',
						justifyContent: 'space-between',
					}}
				>
					<Mono size={21} color={K.muted}>
						$ uv run python demo/run_demo.py
					</Mono>
					<Mono size={21} color={K.faint}>
						in-memory broker · same MCP tools the bots call
					</Mono>
				</div>
				<div style={{height: 690, overflow: 'hidden'}}>
					<div style={{padding: '18px 32px', transform: `translateY(${-scroll}px)`}}>
						{LINES.map((l, i) => {
							if (f < schedule[i]) return null;
							const typed =
								l.tone === 'call'
									? Math.floor(interpolate(f, [schedule[i], schedule[i] + 12], [0, l.text.length], clamp))
									: l.text.length;
							const t = interpolate(f, [schedule[i], schedule[i] + 8], [0, 1], clamp);
							const st = tone[l.tone] ?? tone.plain;
							return (
								<div
									key={i}
									style={{
										height: lh,
										lineHeight: `${lh}px`,
										fontFamily: mono,
										fontSize: S.code,
										whiteSpace: 'pre',
										color: st.color,
										fontWeight: st.weight,
										opacity: l.tone === 'call' ? 1 : t,
										borderLeft: l.tone === 'block' ? `4px solid ${K.accent}` : '4px solid transparent',
										paddingLeft: 14,
									}}
								>
									{l.text.slice(0, typed)}
								</div>
							);
						})}
					</div>
				</div>
			</Slab>
		</Slide>
	);
};

/* 07 — Built tonight */
const metrics: [string, string][] = [
	['7', 'MCP tools'],
	['3', 'detection stages'],
	['76', 'tests passing'],
];
const Built: React.FC = () => (
	<Slide n={7} total={TOTAL}>
		<Eyebrow>07 — Built tonight, 18:00 – 21:00</Eyebrow>
		<div style={{position: 'absolute', left: 0, top: 120, display: 'flex', gap: 0}}>
			{metrics.map(([v, label], i) => (
				<Reveal key={label} at={10 + i * 14}>
					<div
						style={{
							width: 560,
							paddingRight: 40,
							borderLeft: i === 0 ? 'none' : `2px solid ${K.hairline}`,
							paddingLeft: i === 0 ? 0 : 48,
						}}
					>
						<div style={{fontFamily: mono, fontSize: 168, fontWeight: 500, color: K.ink, lineHeight: 1}}>{v}</div>
						<div
							style={{
								fontFamily: display,
								fontWeight: 600,
								fontSize: S.eyebrow,
								letterSpacing: '0.16em',
								textTransform: 'uppercase',
								color: K.muted,
								marginTop: 20,
							}}
						>
							{label}
						</div>
					</div>
				</Reveal>
			))}
		</div>
		<div style={{position: 'absolute', left: 0, bottom: 0}}>
			<Lead at={60} color={K.ink}>
				Python · SQLite · FastMCP over HTTP.
			</Lead>
			<Lead at={74}>Grok Bots join through one public URL. Every agent sees the same graph.</Lead>
		</div>
	</Slide>
);

/* 08 — Close */
const Close: React.FC = () => (
	<Slide n={8} total={TOTAL}>
		<div style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%', gap: 30}}>
			<Eyebrow>GrokMesh · MCP server for Grok Bots</Eyebrow>
			<Title size={S.section} at={8}>
				Sync at <Red>intent</Red>,
			</Title>
			<Title size={S.section} at={22}>
				<span style={{color: K.muted}}>not at the pull request.</span>
			</Title>
			<div style={{marginTop: 40}}>
				<Rule at={40} width={720} />
				<Reveal at={50} style={{marginTop: 22}}>
					<span style={{fontFamily: sans, fontSize: 28, color: K.muted}}>
						Anna Poberezhna · Tsimur Halkin · Marcel Musiałek
					</span>
				</Reveal>
			</div>
		</div>
	</Slide>
);

const T = 12;
const SCENES: [React.FC, number][] = [
	[Opening, 150],
	[Problem, 300],
	[Shift, 230],
	[How, 470],
	[Symbol, 260],
	[Demo, KANZEN_DEMO_FRAMES],
	[Built, 180],
	[Close, 170],
];
export const KANZEN_TOTAL = SCENES.reduce((a, [, d]) => a + d, 0) - T * (SCENES.length - 1);

export const KanzenFilm: React.FC = () => (
	<TransitionSeries>
		{SCENES.map(([Scene, d], i) => (
			<React.Fragment key={i}>
				{i > 0 ? (
					<TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: T})} />
				) : null}
				<TransitionSeries.Sequence durationInFrames={d}>
					<Scene />
				</TransitionSeries.Sequence>
			</React.Fragment>
		))}
	</TransitionSeries>
);
