/**
 * GrokMesh pitch film in the Kanzen design system, dark theme.
 * Bone and graphite, one red spent once per scene, square corners, one 45-degree
 * notch per slab, hairlines instead of boxes. No glow, no gradient.
 * Motion is machined: mask reveals, edge wipes, a shutter between scenes, a slow camera.
 */
import React from 'react';
import {loadFont as loadChakra} from '@remotion/google-fonts/ChakraPetch';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadMono} from '@remotion/google-fonts/JetBrainsMono';
import {AbsoluteFill, Easing, interpolate, Series, useCurrentFrame} from 'remotion';
import demoLines from '../demoLines.json';

const display = loadChakra('normal', {weights: ['600', '700'], subsets: ['latin', 'latin-ext']})
	.fontFamily;
const sans = loadInter('normal', {weights: ['400', '500'], subsets: ['latin', 'latin-ext']}).fontFamily;
const mono = loadMono('normal', {weights: ['400', '500', '700'], subsets: ['latin', 'latin-ext']})
	.fontFamily;

/* Kanzen tokens, dark theme. */
const K = {
	base: '#0B0C0E',
	raised: '#15161A',
	sunken: '#060709',
	ink: '#F2F2EF',
	muted: '#A4A6A0',
	faint: '#74767A',
	accent: '#FF4A3D',
	accentInk: '#0B0C0E',
	hairline: '#2A2B2E',
	grid: '#1E1F23',
};
/* Kanzen sizes ×1.75 for a 1920×1080 frame. */
const S = {eyebrow: 23, title: 78, section: 120, lead: 38, code: 26};
const NOTCH = 24;
const MARGIN = 112;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ease = Easing.bezier(0.2, 0, 0, 1);
const easeIn = Easing.bezier(0.6, 0, 1, 1);

const useT = (start: number, dur = 16, e = ease) => {
	const f = useCurrentFrame();
	return interpolate(f, [start, start + dur], [0, 1], {...clamp, easing: e});
};

/* ── Motion primitives ─────────────────────────────────────────────── */

type Seg = {t: string; c?: string};

/** Words rise one by one from under a mask. */
const Words: React.FC<{segs: Seg[]; at: number; size: number; weight?: number; family?: string; stagger?: number}> = ({
	segs,
	at,
	size,
	weight = 700,
	family = display,
	stagger = 3,
}) => {
	const f = useCurrentFrame();
	const words = segs.flatMap((s) => s.t.split(/(?<= )/).map((w) => ({w, c: s.c ?? K.ink})));
	return (
		<div style={{fontFamily: family, fontWeight: weight, fontSize: size, lineHeight: 1.08, letterSpacing: '-0.015em'}}>
			{words.map((x, i) => {
				const t = interpolate(f, [at + i * stagger, at + i * stagger + 14], [0, 1], {...clamp, easing: ease});
				return (
					<span key={i} style={{display: 'inline-block', overflow: 'hidden', verticalAlign: 'top', paddingBottom: 6}}>
						<span style={{display: 'inline-block', color: x.c, whiteSpace: 'pre', transform: `translateY(${(1 - t) * 105}%)`}}>
							{x.w}
						</span>
					</span>
				);
			})}
		</div>
	);
};

/** A single line slides up from under a mask. */
const Line: React.FC<{at: number; children: React.ReactNode; style?: React.CSSProperties}> = ({at, children, style}) => {
	const t = useT(at, 14);
	return (
		<div style={{overflow: 'hidden', paddingBottom: 4, ...style}}>
			<div style={{transform: `translateY(${(1 - t) * 105}%)`}}>{children}</div>
		</div>
	);
};

const Eyebrow: React.FC<{children: React.ReactNode; at?: number}> = ({children, at = 0}) => {
	const t = useT(at, 18);
	return (
		<div style={{display: 'flex', alignItems: 'center', gap: 18}}>
			<div style={{width: 36 * t, height: 2, background: K.muted}} />
			<Line at={at + 4}>
				<span
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
				</span>
			</Line>
		</div>
	);
};

const Lead: React.FC<{at: number; children: React.ReactNode; color?: string; size?: number}> = ({
	at,
	children,
	color = K.muted,
	size = S.lead,
}) => (
	<Line at={at}>
		<div style={{fontFamily: sans, fontSize: size, lineHeight: 1.45, color}}>{children}</div>
	</Line>
);

const Mono: React.FC<{children: React.ReactNode; size?: number; color?: string; weight?: number}> = ({
	children,
	size = S.code,
	color = K.ink,
	weight = 400,
}) => <span style={{fontFamily: mono, fontSize: size, color, fontWeight: weight, whiteSpace: 'pre'}}>{children}</span>;

const Rule: React.FC<{at: number; width: number; color?: string}> = ({at, width, color = K.hairline}) => {
	const t = useT(at, 22);
	return <div style={{width, height: 2, background: color, transform: `scaleX(${t})`, transformOrigin: 'left'}} />;
};

const notch = (n: number) => `polygon(0 0, calc(100% - ${n}px) 0, 100% ${n}px, 100% 100%, 0 100%)`;

/** A slab revealed by a wiping edge, with one bevelled corner and a hairline edge. */
const Slab: React.FC<{at: number; children: React.ReactNode; style?: React.CSSProperties; fill?: string; edge?: string}> = ({
	at,
	children,
	style,
	fill = K.raised,
	edge = K.hairline,
}) => {
	const t = useT(at, 20);
	const lead = interpolate(t, [0, 1], [0, 100]);
	return (
		<div style={{position: 'relative', clipPath: `inset(0 ${100 - lead}% 0 0)`, ...style}}>
			<div style={{background: edge, clipPath: notch(NOTCH), padding: 2, height: '100%'}}>
				<div style={{background: fill, clipPath: notch(NOTCH - 1), height: '100%'}}>{children}</div>
			</div>
			{t < 1 ? (
				<div style={{position: 'absolute', top: 0, bottom: 0, left: `${lead}%`, width: 2, background: K.ink}} />
			) : null}
		</div>
	);
};

const Counter: React.FC<{to: number; at: number; size: number}> = ({to, at, size}) => {
	const f = useCurrentFrame();
	const v = Math.round(interpolate(f, [at, at + 34], [0, to], {...clamp, easing: Easing.out(Easing.cubic)}));
	return <div style={{fontFamily: mono, fontSize: size, fontWeight: 500, color: K.ink, lineHeight: 1}}>{v}</div>;
};

/* ── Scene chrome: ground, drifting plus-grid, slow camera, footer ──── */

const Scene: React.FC<{
	n: number;
	children: React.ReactNode;
	push?: number;
	origin?: string;
	punch?: {at: number; scale: number};
}> = ({n, children, push = 0.035, origin = '50% 50%', punch}) => {
	const f = useCurrentFrame();
	const cam = interpolate(f, [0, 420], [1, 1 + push], clamp);
	const p = punch ? interpolate(f, [punch.at, punch.at + 24], [1, punch.scale], {...clamp, easing: ease}) : 1;
	return (
		<AbsoluteFill style={{background: K.base, overflow: 'hidden'}}>
			<AbsoluteFill style={{transform: `translateY(${-(f * 0.25) % 48}px)`}}>
				<svg width="1920" height="1128">
					<defs>
						<pattern id={`plus${n}`} width="48" height="48" patternUnits="userSpaceOnUse">
							<path d="M24 19 V29 M19 24 H29" stroke={K.grid} strokeWidth="2" />
						</pattern>
					</defs>
					<rect width="1920" height="1128" fill={`url(#plus${n})`} />
				</svg>
			</AbsoluteFill>
			<AbsoluteFill style={{transform: `scale(${cam * p})`, transformOrigin: origin}}>
				<div style={{position: 'absolute', left: MARGIN, right: MARGIN, top: MARGIN, bottom: 150}}>{children}</div>
			</AbsoluteFill>
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
				<span style={{fontFamily: mono, letterSpacing: 0}}>{String(n).padStart(2, '0')} / 08</span>
			</div>
		</AbsoluteFill>
	);
};

/** Shutter between scenes: a bone slab with a red leading edge crosses the frame. */
const SHUT = 11;
const Shutter: React.FC<{cuts: number[]}> = ({cuts}) => {
	const f = useCurrentFrame();
	const c = cuts.find((x) => f >= x - SHUT && f < x + SHUT);
	if (c === undefined) return null;
	const x =
		f < c
			? interpolate(f, [c - SHUT, c], [-100, 0], {...clamp, easing: easeIn})
			: interpolate(f, [c, c + SHUT], [0, 100], {...clamp, easing: ease});
	return (
		<AbsoluteFill style={{transform: `translateX(${x}%)`}}>
			<div style={{position: 'absolute', inset: 0, background: K.ink, clipPath: notch(120)}} />
			<div style={{position: 'absolute', top: 0, bottom: 0, right: 0, width: 10, background: K.accent}} />
		</AbsoluteFill>
	);
};

/* ── 01 Opening ─────────────────────────────────────────────────────── */
const Opening: React.FC = () => (
	<Scene n={1}>
		<div style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%', gap: 30}}>
			<Eyebrow at={4}>Grok Bot Hackathon · Wrocław</Eyebrow>
			<Words at={12} size={104} segs={[{t: 'Every developer has an AI agent.'}]} />
			<Words at={52} size={104} segs={[{t: 'Every agent codes ', c: K.muted}, {t: 'alone.', c: K.accent}]} />
		</div>
	</Scene>
);

/* ── Timeline shared by 02 and 03 ───────────────────────────────────── */
const AX_L = 330;
const AX_R = 1560;
const lanes = [
	{who: 'anna · agent', y: 120, blocks: ['declare: token expiry', 'issue(user_id, ttl_s)', 'hash_token()']},
	{who: 'marcel · agent', y: 250, blocks: ['rewrite signing', 'issue() → new keys', 'hash_token()  again']},
];

const Timeline: React.FC<{at: number; playhead?: [number, number]}> = ({at, playhead}) => {
	const f = useCurrentFrame();
	const ph = playhead ? interpolate(f, [playhead[0], playhead[1]], [0, 1], clamp) : 1;
	const phX = AX_L + (AX_R - AX_L) * ph;
	const hour = 18 + ph * 3;
	const clock = `${String(Math.floor(hour)).padStart(2, '0')}:${String(Math.floor((hour % 1) * 60)).padStart(2, '0')}`;
	return (
		<>
			{lanes.map((lane, li) => (
				<React.Fragment key={lane.who}>
					<div style={{position: 'absolute', left: 0, top: lane.y + 30}}>
						<Line at={at + li * 6}>
							<Mono size={24} color={K.muted}>
								{lane.who}
							</Mono>
						</Line>
					</div>
					{lane.blocks.map((b, bi) => {
						const x0 = AX_L + bi * 380;
						const w = Math.max(0, Math.min(340, phX - x0 - li * 30));
						return (
							<div
								key={b}
								style={{
									position: 'absolute',
									left: x0,
									top: lane.y,
									width: w,
									height: 96,
									overflow: 'hidden',
									background: K.raised,
									borderTop: `2px solid ${K.ink}`,
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
			<div style={{position: 'absolute', left: AX_L, top: 400}}>
				<Rule at={at} width={AX_R - AX_L} color={K.faint} />
			</div>
			{['18:00', '19:00', '20:00', '21:00'].map((t, i) => (
				<div key={t} style={{position: 'absolute', left: AX_L + i * 400 - 30, top: 416}}>
					<Line at={at + 8}>
						<Mono size={20} color={K.faint}>
							{t}
						</Mono>
					</Line>
				</div>
			))}
			{playhead && ph < 1 ? (
				<div style={{position: 'absolute', left: phX, top: 90, height: 330, width: 2, background: K.muted}}>
					<div style={{position: 'absolute', top: -34, left: -34}}>
						<Mono size={20} color={K.muted}>
							{clock}
						</Mono>
					</div>
				</div>
			) : null}
		</>
	);
};

const Marker: React.FC<{x: number; label: string; sub: string; at: number}> = ({x, label, sub, at}) => {
	const t = useT(at, 12);
	const right = x > 1200;
	const side = right ? {right: -2, textAlign: 'right' as const} : {left: -2};
	return (
		<div style={{position: 'absolute', left: x, top: 90}}>
			<div style={{width: 4, height: 320, background: K.accent, transform: `scaleY(${t})`, transformOrigin: 'top'}} />
			<div
				style={{
					position: 'absolute',
					top: 302,
					left: -8,
					width: 20,
					height: 20,
					background: K.accent,
					transform: `scale(${t})`,
				}}
			/>
			<div style={{position: 'absolute', top: -60, whiteSpace: 'nowrap', opacity: t, ...side}}>
				<Mono size={24} color={K.accent} weight={700}>
					{label}
				</Mono>
			</div>
			<div style={{position: 'absolute', top: -28, whiteSpace: 'nowrap', opacity: t, ...side}}>
				<span style={{fontFamily: sans, fontSize: 22, color: K.muted}}>{sub}</span>
			</div>
		</div>
	);
};

/* ── 02 Problem ─────────────────────────────────────────────────────── */
const Problem: React.FC = () => (
	<Scene n={2} origin="82% 30%" punch={{at: 150, scale: 1.035}} push={0.01}>
		<Eyebrow at={2}>02 — Where it breaks today</Eyebrow>
		<div style={{position: 'absolute', left: 0, right: 0, top: 60, height: 520}}>
			<Timeline at={6} playhead={[14, 150]} />
			<Marker x={AX_R} label="PULL REQUEST" sub="conflict found here" at={150} />
		</div>
		<div style={{position: 'absolute', left: 0, bottom: 0}}>
			<Lead at={172} color={K.ink}>
				Both agents wrote the code. Git compares lines after the fact.
			</Lead>
			<Lead at={186}>Two hours of agent work collide at merge.</Lead>
		</div>
	</Scene>
);

/* ── 03 The idea ────────────────────────────────────────────────────── */
const Shift: React.FC = () => {
	const f = useCurrentFrame();
	const x = interpolate(f, [30, 90], [AX_R, AX_L - 20], {...clamp, easing: Easing.inOut(Easing.cubic)});
	const arrived = f >= 90;
	return (
		<Scene n={3} origin="20% 35%" punch={{at: 92, scale: 1.025}} push={0.01}>
			<Eyebrow at={2}>03 — The idea</Eyebrow>
			<div style={{position: 'absolute', left: 0, right: 0, top: 60, height: 520}}>
				<Timeline at={-200} />
				<Marker x={x} label={arrived ? 'INTENT' : 'PULL REQUEST'} sub={arrived ? 'GrokMesh checks here' : 'today'} at={-20} />
			</div>
			<div style={{position: 'absolute', left: 0, bottom: 0}}>
				<Words at={100} size={62} weight={600} segs={[{t: 'Move the check from the pull request to the intent.'}]} />
				<div style={{marginTop: 18}}>
					<Lead at={128}>Before an agent writes a line, it says what it will change. The broker answers.</Lead>
				</div>
			</div>
		</Scene>
	);
};

/* ── 04 How it works ────────────────────────────────────────────────── */
const COL_W = 500;
const GAP = 98;
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

const Row: React.FC<{at: number; head: string; body: string; last?: boolean; lit?: [number, number]}> = ({
	at,
	head,
	body,
	last,
	lit,
}) => {
	const f = useCurrentFrame();
	const on = lit ? f >= lit[0] && f < lit[1] : false;
	return (
		<div
			style={{
				padding: '16px 30px',
				borderBottom: last ? 'none' : `2px solid ${K.hairline}`,
				background: on ? K.hairline : 'transparent',
			}}
		>
			<Line at={at}>
				<div style={{fontFamily: mono, fontSize: 23, color: K.ink, fontWeight: 500}}>{head}</div>
			</Line>
			<Line at={at + 3}>
				<div style={{fontFamily: sans, fontSize: 21, color: K.muted, marginTop: 4}}>{body}</div>
			</Line>
		</div>
	);
};

/** A small bone packet travels along the arrow between two columns. */
const Packet: React.FC<{at: number; from: number; to: number; y: number}> = ({at, from, to, y}) => {
	const f = useCurrentFrame();
	const t = interpolate(f, [at, at + 22], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
	if (f < at || f > at + 30) return null;
	return <div style={{position: 'absolute', left: from + (to - from) * t - 8, top: y - 8, width: 16, height: 16, background: K.ink}} />;
};

const Arrow: React.FC<{at: number; left: number; top: number}> = ({at, left, top}) => {
	const t = useT(at, 14);
	return (
		<div style={{position: 'absolute', left, top: top - 9, display: 'flex', alignItems: 'center', opacity: t > 0 ? 1 : 0}}>
			<div style={{width: 56 * t, height: 2, background: K.ink}} />
			<div
				style={{
					width: 0,
					height: 0,
					borderTop: '9px solid transparent',
					borderBottom: '9px solid transparent',
					borderLeft: `14px solid ${K.ink}`,
					opacity: t,
				}}
			/>
		</div>
	);
};

const How: React.FC = () => {
	const f = useCurrentFrame();
	const stamp = interpolate(f, [372, 382], [1.14, 1], {...clamp, easing: ease});
	const stampOn = f >= 372;
	const ax = COL_W + 18;
	const bx = 2 * COL_W + GAP + 18;
	return (
		<Scene n={4} push={0.025}>
			<Eyebrow at={2}>04 — How it works</Eyebrow>
			<div style={{position: 'absolute', left: 0, top: 70, display: 'flex', gap: GAP}}>
				<Slab at={10} style={{width: COL_W, height: 640}}>
					<ColHead n="A" title="Agents" sub="Each Grok Bot calls the broker over MCP." />
					<Row at={30} head="declare_intent()" body="symbols it will produce or modify" lit={[80, 112]} />
					<Row at={40} head="sync_file()" body="the changed file, after each edit" lit={[190, 222]} />
					<Row at={50} head="get_contracts()" body="current signatures before a call" />
					<Row at={60} head="get_activity()" body="Mesh Bot: who works on what" last />
				</Slab>
				<Slab at={112} style={{width: COL_W, height: 640}}>
					<ColHead n="B" title="Live code graph" sub="Symbols, signatures, call edges. No source kept." />
					<Row at={132} head="base" body="main branch, parsed at start" />
					<Row at={142} head="overlay · anna" body="her uncommitted symbols" lit={[222, 254]} />
					<Row at={152} head="overlay · marcel" body="his uncommitted symbols" />
					<Row at={162} head="leases" body="claims on symbols, 30 min TTL" last />
				</Slab>
				<Slab at={232} style={{width: COL_W, height: 640}}>
					<ColHead n="C" title="Checks" sub="Cheap and exact first. Fuzzy last." />
					<Row at={252} head="1  same symbol" body="two active claims on one function" lit={[300, 324]} />
					<Row at={262} head="2  broken contract" body="signature diff + a calls edge" lit={[324, 348]} />
					<Row at={272} head="3  duplication" body="BM25 match against other intents" lit={[348, 372]} />
					<div style={{margin: '22px 30px', height: 54}}>
						{stampOn ? (
							<div
								style={{
									padding: '14px 20px',
									background: K.accent,
									color: K.accentInk,
									fontFamily: mono,
									fontWeight: 700,
									fontSize: 23,
									transform: `scale(${stamp})`,
									transformOrigin: 'left center',
								}}
							>
								BLOCK / WARN + resolution
							</div>
						) : null}
					</div>
				</Slab>
			</div>
			<Arrow at={96} left={ax} top={460} />
			<Arrow at={214} left={bx} top={460} />
			<Packet at={100} from={ax} to={ax + 70} y={460} />
			<Packet at={218} from={bx} to={bx + 70} y={460} />
			<div style={{position: 'absolute', left: 0, bottom: 0}}>
				<Lead at={392}>Stages 1 and 2 can block an edit. Stage 3 only warns.</Lead>
			</div>
		</Scene>
	);
};

/* ── 05 The unit is a symbol ────────────────────────────────────────── */
const fields: [string, string, boolean?][] = [
	['signature', 'def issue(user_id: str, ttl_s: int) -> str'],
	['on main', 'def issue(user_id: str) -> str'],
	['change', 'breaking', true],
	['owner', 'anna · lease, 30 min'],
	['called by', 'demo.api.login   (marcel is editing it)'],
];

const SymbolCard: React.FC = () => {
	const f = useCurrentFrame();
	const hl = interpolate(f, [104, 124], [0, 100], {...clamp, easing: ease});
	return (
		<Scene n={5} push={0.03} origin="30% 40%">
			<Eyebrow at={2}>05 — The unit is a symbol, not a file</Eyebrow>
			<div style={{position: 'absolute', left: 0, top: 80, width: 1120}}>
				<Slab at={8} style={{width: 1120}}>
					<div
						style={{
							padding: '30px 40px',
							borderBottom: `2px solid ${K.hairline}`,
							display: 'flex',
							justifyContent: 'space-between',
							alignItems: 'baseline',
						}}
					>
						<Line at={20}>
							<Mono size={40} weight={700}>
								demo.auth.issue
							</Mono>
						</Line>
						<Line at={26}>
							<Mono size={22} color={K.faint}>
								function · demo/auth.py
							</Mono>
						</Line>
					</div>
					{fields.map(([k, v, red], i) => (
						<div
							key={k}
							style={{
								position: 'relative',
								display: 'flex',
								padding: '20px 40px',
								borderBottom: i === fields.length - 1 ? 'none' : `2px solid ${K.hairline}`,
							}}
						>
							{red ? (
								<div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${hl}%`, background: K.hairline}} />
							) : null}
							<div style={{width: 230, position: 'relative'}}>
								<Line at={34 + i * 14}>
									<Mono size={24} color={K.muted}>
										{k}
									</Mono>
								</Line>
							</div>
							<div style={{position: 'relative'}}>
								<Line at={38 + i * 14}>
									<Mono size={27} color={red ? K.accent : K.ink} weight={red ? 700 : 400}>
										{v}
									</Mono>
								</Line>
							</div>
						</div>
					))}
				</Slab>
			</div>
			<div style={{position: 'absolute', left: 1200, top: 110, width: 490, display: 'flex', flexDirection: 'column', gap: 24}}>
				<Words at={130} size={34} weight={500} family={sans} stagger={2} segs={[{t: 'The broker diffs signatures and follows call edges.'}]} />
				<Words
					at={160}
					size={30}
					weight={400}
					family={sans}
					stagger={2}
					segs={[{t: "That is how a change in one agent's work reaches another agent's caller, before either one commits.", c: K.muted}]}
				/>
			</div>
		</Scene>
	);
};

/* ── 06 Live demo: the real output of demo/run_demo.py ──────────────── */
type DemoLine = {text: string; tone: string};
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
const LINES = demoLines as DemoLine[];
const schedule = (() => {
	let t = 30;
	return LINES.map((l) => {
		if (l.tone === 'step') t += 18;
		const s = t;
		t += l.text === '' ? 4 : l.tone === 'call' ? 16 : 11;
		return s;
	});
})();
const DEMO_FRAMES = schedule[schedule.length - 1] + 80;

const Demo: React.FC = () => {
	const f = useCurrentFrame();
	const rows = 19;
	const lh = 36;
	const scroll =
		LINES.reduce((acc, _, i) => (i < rows ? acc : acc + interpolate(f, [schedule[i], schedule[i] + 10], [0, 1], {...clamp, easing: ease})), 0) *
		lh;
	const cursorRow = LINES.filter((_, i) => f >= schedule[i]).length;
	return (
		<Scene n={6} push={0.02}>
			<Eyebrow at={2}>06 — Live demo · two agents, one broker</Eyebrow>
			<Slab at={6} fill={K.sunken} style={{position: 'absolute', left: 0, right: 0, top: 60, height: 760}}>
				<div style={{padding: '16px 32px', borderBottom: `2px solid ${K.hairline}`, display: 'flex', justifyContent: 'space-between'}}>
					<Mono size={21} color={K.muted}>
						$ uv run python demo/run_demo.py
					</Mono>
					<Mono size={21} color={K.faint}>
						in-memory broker · the same MCP tools the bots call
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
							const t = interpolate(f, [schedule[i], schedule[i] + 8], [0, 1], {...clamp, easing: ease});
							const st = tone[l.tone] ?? tone.plain;
							const isBlock = l.tone === 'block';
							return (
								<div
									key={i}
									style={{
										position: 'relative',
										height: lh,
										lineHeight: `${lh}px`,
										fontFamily: mono,
										fontSize: S.code,
										whiteSpace: 'pre',
										color: st.color,
										fontWeight: st.weight,
										paddingLeft: 18,
										opacity: l.tone === 'call' ? 1 : t,
										transform: l.tone === 'call' ? 'none' : `translateX(${(1 - t) * -12}px)`,
									}}
								>
									{isBlock ? (
										<div style={{position: 'absolute', left: 0, top: 4, bottom: 4, width: 4, background: K.accent, transform: `scaleY(${t})`}} />
									) : null}
									{l.text.slice(0, typed)}
									{i === cursorRow - 1 && Math.floor(f / 8) % 2 === 0 ? (
										<span style={{display: 'inline-block', width: 14, height: 26, background: K.muted, marginLeft: 4, verticalAlign: 'middle'}} />
									) : null}
								</div>
							);
						})}
					</div>
				</div>
			</Slab>
		</Scene>
	);
};

/* ── 07 Built tonight ───────────────────────────────────────────────── */
const metrics: [number, string][] = [
	[7, 'MCP tools'],
	[3, 'detection stages'],
	[76, 'tests passing'],
];
const Built: React.FC = () => (
	<Scene n={7} push={0.03}>
		<Eyebrow at={2}>07 — Built tonight, 18:00 – 21:00</Eyebrow>
		<div style={{position: 'absolute', left: 0, top: 120, display: 'flex'}}>
			{metrics.map(([v, label], i) => (
				<div
					key={label}
					style={{
						width: 560,
						paddingLeft: i === 0 ? 0 : 48,
						borderLeft: i === 0 ? 'none' : `2px solid ${K.hairline}`,
					}}
				>
					<Counter to={v} at={10 + i * 10} size={168} />
					<div style={{marginTop: 20}}>
						<Line at={20 + i * 10}>
							<span
								style={{
									fontFamily: display,
									fontWeight: 600,
									fontSize: S.eyebrow,
									letterSpacing: '0.16em',
									textTransform: 'uppercase',
									color: K.muted,
								}}
							>
								{label}
							</span>
						</Line>
					</div>
				</div>
			))}
		</div>
		<div style={{position: 'absolute', left: 0, bottom: 0}}>
			<Lead at={64} color={K.ink}>
				Python · SQLite · FastMCP over HTTP.
			</Lead>
			<Lead at={76}>Grok Bots join through one public URL. Every agent sees the same graph.</Lead>
		</div>
	</Scene>
);

/* ── 08 Close ───────────────────────────────────────────────────────── */
const Close: React.FC = () => (
	<Scene n={8} push={0.04}>
		<div style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%', gap: 26}}>
			<Eyebrow at={2}>GrokMesh · MCP server for Grok Bots</Eyebrow>
			<Words at={10} size={S.section} segs={[{t: 'Sync at '}, {t: 'intent', c: K.accent}, {t: ','}]} />
			<Words at={26} size={S.section} segs={[{t: 'not at the pull request.', c: K.muted}]} />
			<div style={{marginTop: 40}}>
				<Rule at={52} width={720} />
				<div style={{marginTop: 22}}>
					<Lead at={62} size={28}>
						Anna Poberezhna · Tsimur Halkin · Marcel Musiałek
					</Lead>
				</div>
			</div>
		</div>
	</Scene>
);

const SCENES: [React.FC, number][] = [
	[Opening, 140],
	[Problem, 280],
	[Shift, 220],
	[How, 460],
	[SymbolCard, 250],
	[Demo, DEMO_FRAMES],
	[Built, 170],
	[Close, 170],
];
const CUTS = SCENES.slice(0, -1).reduce<number[]>((acc, [, d]) => [...acc, (acc.at(-1) ?? 0) + d], []);
export const KANZEN_TOTAL = SCENES.reduce((a, [, d]) => a + d, 0);

export const KanzenFilm: React.FC = () => (
	<AbsoluteFill style={{background: K.base}}>
		<Series>
			{SCENES.map(([Scene_, d], i) => (
				<Series.Sequence key={i} durationInFrames={d}>
					<Scene_ />
				</Series.Sequence>
			))}
		</Series>
		<Shutter cuts={CUTS} />
	</AbsoluteFill>
);
