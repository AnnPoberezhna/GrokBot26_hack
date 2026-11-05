/**
 * GrokMesh pitch film in the Kanzen design system, dark theme.
 * One continuous take: the camera glides down a single canvas from section to
 * section, and each section builds as the camera arrives. One red per section,
 * square corners, one bevel per slab, hairlines instead of boxes. No glow.
 */
import React from 'react';
import {loadFont as loadChakra} from '@remotion/google-fonts/ChakraPetch';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadMono} from '@remotion/google-fonts/JetBrainsMono';
import {AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame} from 'remotion';
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
const S = {eyebrow: 23, title: 78, section: 112, lead: 36, code: 26};
const W = 1920;
const H = 1080;
const NOTCH = 24;
const MARGIN = 112;
const LEAD = 30; // frames a section is mounted before the camera arrives
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ease = Easing.bezier(0.2, 0, 0, 1);
const glide = Easing.bezier(0.65, 0, 0.35, 1);

/** Section-local frame: 0 is the moment the camera arrives. */
const useF = () => useCurrentFrame() - LEAD;
const useT = (start: number, dur = 18) => {
	const f = useF();
	return interpolate(f, [start, start + dur], [0, 1], {...clamp, easing: ease});
};

/* ── Primitives ─────────────────────────────────────────────────────── */

type Seg = {t: string; c?: string};
const Words: React.FC<{segs: Seg[]; at: number; size: number; weight?: number; family?: string; stagger?: number}> = ({
	segs,
	at,
	size,
	weight = 700,
	family = display,
	stagger = 3,
}) => {
	const f = useF();
	const words = segs.flatMap((s) => s.t.split(/(?<= )/).map((w) => ({w, c: s.c ?? K.ink})));
	return (
		<div style={{fontFamily: family, fontWeight: weight, fontSize: size, lineHeight: 1.1, letterSpacing: '-0.015em'}}>
			{words.map((x, i) => {
				const t = interpolate(f, [at + i * stagger, at + i * stagger + 20], [0, 1], {...clamp, easing: ease});
				return (
					<span
						key={i}
						style={{
							display: 'inline-block',
							whiteSpace: 'pre',
							color: x.c,
							opacity: t,
							transform: `translateY(${(1 - t) * 0.35}em)`,
						}}
					>
						{x.w}
					</span>
				);
			})}
		</div>
	);
};

const Fade: React.FC<{at: number; children: React.ReactNode; style?: React.CSSProperties; dy?: number}> = ({
	at,
	children,
	style,
	dy = 14,
}) => {
	const t = useT(at, 22);
	return <div style={{opacity: t, transform: `translateY(${(1 - t) * dy}px)`, ...style}}>{children}</div>;
};

const Eyebrow: React.FC<{children: React.ReactNode; at?: number}> = ({children, at = 0}) => {
	const t = useT(at, 24);
	return (
		<div style={{display: 'flex', alignItems: 'center', gap: 18, opacity: t}}>
			<div style={{width: 36 * t, height: 2, background: K.muted}} />
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
		</div>
	);
};

const Lead: React.FC<{at: number; children: React.ReactNode; color?: string; size?: number}> = ({
	at,
	children,
	color = K.muted,
	size = S.lead,
}) => (
	<Fade at={at}>
		<div style={{fontFamily: sans, fontSize: size, lineHeight: 1.45, color}}>{children}</div>
	</Fade>
);

const Mono: React.FC<{children: React.ReactNode; size?: number; color?: string; weight?: number}> = ({
	children,
	size = S.code,
	color = K.ink,
	weight = 400,
}) => <span style={{fontFamily: mono, fontSize: size, color, fontWeight: weight, whiteSpace: 'pre'}}>{children}</span>;

const notch = (n: number) => `polygon(0 0, calc(100% - ${n}px) 0, 100% ${n}px, 100% 100%, 0 100%)`;

const Slab: React.FC<{at: number; children: React.ReactNode; style?: React.CSSProperties; fill?: string; edge?: string}> = ({
	at,
	children,
	style,
	fill = K.raised,
	edge = K.hairline,
}) => {
	const t = useT(at, 26);
	return (
		<div style={{opacity: t, transform: `translateY(${(1 - t) * 24}px)`, ...style}}>
			<div style={{background: edge, clipPath: notch(NOTCH), padding: 2, height: '100%'}}>
				<div style={{background: fill, clipPath: notch(NOTCH - 1), height: '100%'}}>{children}</div>
			</div>
		</div>
	);
};

const SlabHead: React.FC<{kicker: string; title: string; sub?: string}> = ({kicker, title, sub}) => (
	<div style={{padding: '24px 30px 18px', borderBottom: `2px solid ${K.hairline}`}}>
		<div
			style={{
				fontFamily: display,
				fontWeight: 600,
				fontSize: 19,
				letterSpacing: '0.16em',
				textTransform: 'uppercase',
				color: K.faint,
			}}
		>
			{kicker}
		</div>
		<div style={{fontFamily: display, fontWeight: 600, fontSize: 36, color: K.ink, marginTop: 6}}>{title}</div>
		{sub ? <div style={{fontFamily: sans, fontSize: 22, color: K.muted, marginTop: 6}}>{sub}</div> : null}
	</div>
);

/** Code lines that type in one after another. */
const Code: React.FC<{lines: {t: string; c?: string}[]; at: number; per?: number; size?: number}> = ({
	lines,
	at,
	per = 9,
	size = 25,
}) => {
	const f = useF();
	return (
		<div style={{padding: '20px 30px'}}>
			{lines.map((l, i) => {
				const s = at + i * per;
				const n = Math.floor(interpolate(f, [s, s + per], [0, l.t.length], clamp));
				return (
					<div key={i} style={{height: 40, lineHeight: '40px'}}>
						<Mono size={size} color={l.c ?? K.ink}>
							{l.t.slice(0, n)}
						</Mono>
					</div>
				);
			})}
		</div>
	);
};

/* ── 01 Opening ─────────────────────────────────────────────────────── */
const Opening: React.FC = () => (
	<div style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%', gap: 30}}>
		<Eyebrow at={0}>Grok Bot Hackathon · Wrocław</Eyebrow>
		<Words at={8} size={S.section} segs={[{t: 'Every developer has a Grok Bot.'}]} />
		<Words at={40} size={S.section} segs={[{t: 'Every bot codes ', c: K.muted}, {t: 'alone.', c: K.accent}]} />
	</div>
);

/* ── 02 Two tasks, one contract ─────────────────────────────────────── */
const COL = 760;
const TwoTasks: React.FC = () => {
	const f = useF();
	const merge = interpolate(f, [150, 190], [0, 1], {...clamp, easing: ease});
	const midX = COL + (W - 2 * MARGIN - 2 * COL) / 2;
	return (
		<>
			<Eyebrow at={0}>02 — Two tasks, one contract</Eyebrow>
			<div style={{position: 'absolute', left: 0, top: 70, display: 'flex', gap: W - 2 * MARGIN - 2 * COL}}>
				<Slab at={10} style={{width: COL, height: 470}}>
					<SlabHead kicker="Frontend · Anna's Grok Bot" title="Task: login form" />
					<Code
						at={30}
						lines={[
							{t: '# client/auth.py', c: K.faint},
							{t: 'def sign_in(user_id):'},
							{t: '    res = api.login(user_id)'},
							{t: '    return res["token"]'},
						]}
					/>
					<Fade at={80} style={{padding: '0 30px'}}>
						<Mono size={22} color={K.muted}>
							✓ task done · tests pass
						</Mono>
					</Fade>
				</Slab>
				<Slab at={24} style={{width: COL, height: 470}}>
					<SlabHead kicker="Backend · Tim's Grok Bot" title="Task: token expiry" />
					<Code
						at={44}
						lines={[
							{t: '# api.py', c: K.faint},
							{t: 'def login(user_id, password):'},
							{t: '    exp = now() + TTL'},
							{t: '    return {"token": t, "expires_at": exp}'},
						]}
					/>
					<Fade at={94} style={{padding: '0 30px'}}>
						<Mono size={22} color={K.muted}>
							✓ task done · tests pass
						</Mono>
					</Fade>
				</Slab>
			</div>
			<svg width={W - 2 * MARGIN} height={300} style={{position: 'absolute', left: 0, top: 540}}>
				<path
					d={`M ${COL / 2} 0 C ${COL / 2} 90, ${midX} 50, ${midX} 120`}
					stroke={K.faint}
					strokeWidth={2}
					fill="none"
					pathLength={1}
					strokeDasharray={1}
					strokeDashoffset={1 - merge}
				/>
				<path
					d={`M ${W - 2 * MARGIN - COL / 2} 0 C ${W - 2 * MARGIN - COL / 2} 90, ${midX} 50, ${midX} 120`}
					stroke={K.faint}
					strokeWidth={2}
					fill="none"
					pathLength={1}
					strokeDasharray={1}
					strokeDashoffset={1 - merge}
				/>
			</svg>
			<div style={{position: 'absolute', left: midX - 480, top: 680, width: 960, textAlign: 'center'}}>
				<Fade at={186}>
					<Mono size={22} color={K.faint}>
						merge
					</Mono>
				</Fade>
				<Fade at={196} style={{marginTop: 10}}>
					<Mono size={30} color={K.accent} weight={700}>
						login(user_id)  ≠  login(user_id, password)
					</Mono>
				</Fade>
				<Fade at={214} style={{marginTop: 14}}>
					<span style={{fontFamily: sans, fontSize: 30, color: K.ink}}>
						Different tasks. Same endpoint. Broken at merge.
					</span>
				</Fade>
			</div>
		</>
	);
};

/* ── 03 The bots check each other, in flight ────────────────────────── */
const Bubble: React.FC<{at: number; who: string; children: React.ReactNode; me?: boolean}> = ({at, who, children, me}) => (
	<Fade at={at} style={{alignSelf: me ? 'flex-end' : 'flex-start', maxWidth: 680}}>
		<div style={{fontFamily: mono, fontSize: 18, color: K.faint, marginBottom: 6, textAlign: me ? 'right' : 'left'}}>{who}</div>
		<div
			style={{
				fontFamily: sans,
				fontSize: 25,
				lineHeight: 1.45,
				color: K.ink,
				padding: '14px 20px',
				background: me ? K.hairline : 'transparent',
				borderLeft: me ? 'none' : `2px solid ${K.muted}`,
			}}
		>
			{children}
		</div>
	</Fade>
);

const InFlight: React.FC = () => {
	const f = useF();
	const fix = interpolate(f, [300, 330], [0, 1], {...clamp, easing: ease});
	const oldCall = '    res = api.login(user_id)';
	const newCall = '    res = api.login(user_id, password)';
	const shown = fix < 0.5 ? oldCall : newCall.slice(0, oldCall.length + Math.round((newCall.length - oldCall.length) * fix));
	return (
		<>
			<Eyebrow at={0}>03 — With GrokMesh, the bots check each other in flight</Eyebrow>
			<div style={{position: 'absolute', left: 0, top: 70, display: 'flex', gap: 56}}>
				<Slab at={8} style={{width: 860, height: 760}} fill={K.raised}>
					<SlabHead kicker="Grok Bot · Anna" title="Wire the login form" />
					<div style={{padding: '22px 30px', display: 'flex', flexDirection: 'column', gap: 18}}>
						<Bubble at={24} who="anna" me>
							Wire the login form to the API.
						</Bubble>
						<Bubble at={60} who="grok bot">
							Before I write it, I&apos;ll check GrokMesh for the current contract.
						</Bubble>
						<Fade at={96}>
							<div style={{borderTop: `2px solid ${K.hairline}`, borderBottom: `2px solid ${K.hairline}`, padding: '12px 0'}}>
								<Mono size={21} color={K.muted}>
									→ get_contracts([&quot;api.login&quot;])
								</Mono>
								<div style={{marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6}}>
									<div>
										<Mono size={22} color={K.faint}>
											{'main          '}
										</Mono>
										<Mono size={22}>def login(user_id)</Mono>
									</div>
									<Fade at={120} dy={6}>
										<Mono size={22} color={K.faint}>
											{'tim · editing '}
										</Mono>
										<Mono size={22} color={K.accent} weight={700}>
											def login(user_id, password)
										</Mono>
									</Fade>
								</div>
							</div>
						</Fade>
						<Bubble at={160} who="grok bot">
							Tim is changing login() right now: it needs a password and returns expires_at. I&apos;ll use the new
							contract.
						</Bubble>
					</div>
				</Slab>
				<div style={{display: 'flex', flexDirection: 'column', gap: 30, width: 810}}>
					<Slab at={220} style={{width: 810, height: 300}}>
						<SlabHead kicker="Frontend · client/auth.py" title="Adapted on the fly" />
						<div style={{padding: '18px 30px'}}>
							{['def sign_in(user_id, password):', shown, '    return res["token"]'].map((l, i) => (
								<div key={i} style={{height: 40, lineHeight: '40px'}}>
									<Mono size={25} color={i === 1 && fix > 0.5 ? K.ink : K.ink}>
										{i === 0 && fix < 0.5 ? 'def sign_in(user_id):' : l}
									</Mono>
								</div>
							))}
						</div>
					</Slab>
					<div style={{marginTop: 10}}>
						<Words
							at={340}
							size={46}
							weight={600}
							segs={[{t: 'Different tasks. Same contract.'}, {t: ' Matched before either one commits.', c: K.muted}]}
						/>
					</div>
				</div>
			</div>
		</>
	);
};

/* ── 04 How it works ────────────────────────────────────────────────── */
const COL3 = 500;
const GAP3 = 98;
const Row: React.FC<{at: number; head: string; body: string; last?: boolean; lit?: [number, number]}> = ({
	at,
	head,
	body,
	last,
	lit,
}) => {
	const f = useF();
	const on = lit ? interpolate(f, [lit[0], lit[0] + 8, lit[1] - 8, lit[1]], [0, 1, 1, 0], clamp) : 0;
	return (
		<div style={{position: 'relative', padding: '16px 30px', borderBottom: last ? 'none' : `2px solid ${K.hairline}`}}>
			<div style={{position: 'absolute', inset: 0, background: K.hairline, opacity: on}} />
			<Fade at={at} dy={8} style={{position: 'relative'}}>
				<div style={{fontFamily: mono, fontSize: 23, color: K.ink, fontWeight: 500}}>{head}</div>
				<div style={{fontFamily: sans, fontSize: 21, color: K.muted, marginTop: 4}}>{body}</div>
			</Fade>
		</div>
	);
};

const Flow: React.FC<{at: number; x: number; y: number}> = ({at, x, y}) => {
	const f = useF();
	const t = useT(at, 20);
	const dot = ((f - at) % 40) / 40;
	return (
		<div style={{position: 'absolute', left: x, top: y, width: 70, height: 2, background: K.faint, opacity: t}}>
			{f > at + 20 ? (
				<div style={{position: 'absolute', left: dot * 62, top: -5, width: 12, height: 12, background: K.ink}} />
			) : null}
		</div>
	);
};

const How: React.FC = () => {
	const f = useF();
	const v = useT(330, 20);
	const ax = COL3 + 14;
	const bx = 2 * COL3 + GAP3 + 14;
	return (
		<>
			<Eyebrow at={0}>04 — How it works</Eyebrow>
			<div style={{position: 'absolute', left: 0, top: 70, display: 'flex', gap: GAP3}}>
				<Slab at={10} style={{width: COL3, height: 640}}>
					<SlabHead kicker="A" title="Grok Bots" sub="Each bot calls the broker over MCP." />
					<Row at={30} head="declare_intent()" body="symbols it will produce or modify" lit={[90, 130]} />
					<Row at={38} head="sync_file()" body="the changed file, after each edit" lit={[190, 230]} />
					<Row at={46} head="get_contracts()" body="current signatures, WIP included" />
					<Row at={54} head="get_activity()" body="Mesh Bot: who works on what" last />
				</Slab>
				<Slab at={100} style={{width: COL3, height: 640}}>
					<SlabHead kicker="B" title="Live code graph" sub="Symbols, signatures, call edges. No source kept." />
					<Row at={120} head="base" body="main branch, parsed at start" />
					<Row at={128} head="overlay · anna" body="her uncommitted symbols" lit={[230, 270]} />
					<Row at={136} head="overlay · tim" body="his uncommitted symbols" />
					<Row at={144} head="leases" body="claims on symbols, 30 min TTL" last />
				</Slab>
				<Slab at={200} style={{width: COL3, height: 640}}>
					<SlabHead kicker="C" title="Checks" sub="Exact first, fuzzy last." />
					<Row at={220} head="1  same symbol" body="two active claims on one function" lit={[260, 290]} />
					<Row at={228} head="2  broken contract" body="signature diff + a calls edge" lit={[285, 315]} />
					<Row at={236} head="3  duplication" body="BM25 match against other intents" lit={[310, 340]} />
					<div style={{margin: '22px 30px', opacity: v, transform: `translateY(${(1 - v) * 10}px)`}}>
						<div
							style={{
								padding: '14px 20px',
								background: K.accent,
								color: K.accentInk,
								fontFamily: mono,
								fontWeight: 700,
								fontSize: 23,
							}}
						>
							BLOCK / WARN + resolution
						</div>
					</div>
				</Slab>
			</div>
			<Flow at={90} x={ax} y={440} />
			<Flow at={190} x={bx} y={440} />
			<div style={{position: 'absolute', left: 0, bottom: 0, opacity: f > 0 ? 1 : 0}}>
				<Lead at={360}>Stages 1 and 2 can block an edit. Stage 3 only warns.</Lead>
			</div>
		</>
	);
};

/* ── 05 Real run: demo/run_demo.py ──────────────────────────────────── */
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
	let t = 24;
	return LINES.map((l) => {
		if (l.tone === 'step') t += 18;
		const s = t;
		t += l.text === '' ? 4 : l.tone === 'call' ? 16 : 11;
		return s;
	});
})();
const DEMO_FRAMES = schedule[schedule.length - 1] + 70;

const Demo: React.FC = () => {
	const f = useF();
	const rows = 19;
	const lh = 36;
	const scroll =
		LINES.reduce(
			(acc, _, i) => (i < rows ? acc : acc + interpolate(f, [schedule[i], schedule[i] + 14], [0, 1], {...clamp, easing: ease})),
			0,
		) * lh;
	return (
		<>
			<Eyebrow at={0}>05 — Real run · two agents, one broker</Eyebrow>
			<Slab at={6} fill={K.sunken} style={{position: 'absolute', left: 0, right: 0, top: 60, height: 760}}>
				<div style={{padding: '16px 32px', borderBottom: `2px solid ${K.hairline}`, display: 'flex', justifyContent: 'space-between'}}>
					<Mono size={21} color={K.muted}>
						$ uv run python demo/run_demo.py
					</Mono>
					<Mono size={21} color={K.faint}>
						the same MCP tools the Grok Bots call
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
							const t = interpolate(f, [schedule[i], schedule[i] + 10], [0, 1], {...clamp, easing: ease});
							const st = tone[l.tone] ?? tone.plain;
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
									}}
								>
									{l.tone === 'block' ? (
										<div style={{position: 'absolute', left: 0, top: 4, bottom: 4, width: 4, background: K.accent}} />
									) : null}
									{l.text.slice(0, typed)}
								</div>
							);
						})}
					</div>
				</div>
			</Slab>
		</>
	);
};

/* ── 06 Built tonight ───────────────────────────────────────────────── */
const metrics: [number, string][] = [
	[7, 'MCP tools'],
	[3, 'detection stages'],
	[76, 'tests passing'],
];
const Counter: React.FC<{to: number; at: number}> = ({to, at}) => {
	const f = useF();
	const v = Math.round(interpolate(f, [at, at + 40], [0, to], {...clamp, easing: Easing.out(Easing.cubic)}));
	return <div style={{fontFamily: mono, fontSize: 168, fontWeight: 500, color: K.ink, lineHeight: 1}}>{v}</div>;
};
const Built: React.FC = () => (
	<>
		<Eyebrow at={0}>06 — Built tonight, 18:00 – 21:00</Eyebrow>
		<div style={{position: 'absolute', left: 0, top: 120, display: 'flex'}}>
			{metrics.map(([v, label], i) => (
				<Fade key={label} at={6 + i * 8} style={{width: 560, paddingLeft: i === 0 ? 0 : 48, borderLeft: i === 0 ? 'none' : `2px solid ${K.hairline}`}}>
					<Counter to={v} at={8 + i * 8} />
					<div
						style={{
							marginTop: 20,
							fontFamily: display,
							fontWeight: 600,
							fontSize: S.eyebrow,
							letterSpacing: '0.16em',
							textTransform: 'uppercase',
							color: K.muted,
						}}
					>
						{label}
					</div>
				</Fade>
			))}
		</div>
		<div style={{position: 'absolute', left: 0, bottom: 0}}>
			<Lead at={50} color={K.ink}>
				Python · SQLite · FastMCP over Streamable HTTP.
			</Lead>
			<Lead at={62}>Every Grok Bot joins through one public URL and sees the same live graph.</Lead>
		</div>
	</>
);

/* ── 07 Close ───────────────────────────────────────────────────────── */
const Close: React.FC = () => (
	<div style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%', gap: 26}}>
		<Eyebrow at={0}>GrokMesh · MCP server for Grok Bots</Eyebrow>
		<Words at={8} size={S.section} segs={[{t: 'Sync at '}, {t: 'intent', c: K.accent}, {t: ','}]} />
		<Words at={22} size={S.section} segs={[{t: 'not at the pull request.', c: K.muted}]} />
		<Fade at={56} style={{marginTop: 40}}>
			<div style={{width: 720, height: 2, background: K.hairline, marginBottom: 22}} />
			<span style={{fontFamily: sans, fontSize: 28, color: K.muted}}>Anna Poberezhna · Tsimur Halkin · Marcel Musiałek</span>
		</Fade>
	</div>
);

/* ── One continuous take ────────────────────────────────────────────── */
const SECTIONS: [React.FC, number][] = [
	[Opening, 130],
	[TwoTasks, 290],
	[InFlight, 430],
	[How, 410],
	[Demo, DEMO_FRAMES],
	[Built, 160],
	[Close, 170],
];
const STARTS = SECTIONS.reduce<number[]>((acc, [, d], i) => [...acc, i === 0 ? 0 : acc[i - 1] + SECTIONS[i - 1][1]], []);
export const KANZEN_TOTAL = STARTS[STARTS.length - 1] + SECTIONS[SECTIONS.length - 1][1];
const GLIDE = 40;

export const KanzenFilm: React.FC = () => {
	const f = useCurrentFrame();
	const camY = STARTS.slice(1).reduce(
		(acc, s) => acc + interpolate(f, [s - GLIDE + 10, s + 10], [0, H], {...clamp, easing: glide}),
		0,
	);
	const current = STARTS.filter((s) => f >= s - 10).length;
	return (
		<AbsoluteFill style={{background: K.base, overflow: 'hidden'}}>
			<AbsoluteFill style={{transform: `translateY(${-(camY * 0.6) % 48}px)`}}>
				<svg width={W} height={H + 96}>
					<defs>
						<pattern id="plus" width="48" height="48" patternUnits="userSpaceOnUse">
							<path d="M24 19 V29 M19 24 H29" stroke={K.grid} strokeWidth="2" />
						</pattern>
					</defs>
					<rect width={W} height={H + 96} fill="url(#plus)" />
				</svg>
			</AbsoluteFill>
			<div style={{position: 'absolute', left: 0, top: 0, width: W, transform: `translateY(${-camY}px)`}}>
				{SECTIONS.map(([Section, d], i) => (
					<Sequence key={i} from={STARTS[i] - LEAD} durationInFrames={d + LEAD + GLIDE} layout="none">
						<div style={{position: 'absolute', left: MARGIN, right: MARGIN, top: i * H + MARGIN, height: H - MARGIN - 150}}>
							<Section />
						</div>
					</Sequence>
				))}
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
					background: K.base,
				}}
			>
				<span>GrokMesh</span>
				<span style={{fontFamily: mono, letterSpacing: 0}}>
					{String(current).padStart(2, '0')} / {String(SECTIONS.length).padStart(2, '0')}
				</span>
			</div>
		</AbsoluteFill>
	);
};
