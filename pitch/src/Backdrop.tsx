import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {C} from './theme';

/** Dark cinematic backdrop: drifting glows, faint grid, grain and vignette. */
export const Backdrop: React.FC<{glow?: string; glow2?: string}> = ({
	glow = C.violet,
	glow2 = C.anna,
}) => {
	const f = useCurrentFrame();
	const x1 = 30 + Math.sin(f / 90) * 8;
	const y1 = 35 + Math.cos(f / 110) * 6;
	const x2 = 70 + Math.cos(f / 100) * 8;
	const y2 = 65 + Math.sin(f / 120) * 6;
	return (
		<AbsoluteFill style={{backgroundColor: C.bg, overflow: 'hidden'}}>
			<AbsoluteFill
				style={{
					background: `radial-gradient(900px circle at ${x1}% ${y1}%, ${glow}22, transparent 60%),
            radial-gradient(800px circle at ${x2}% ${y2}%, ${glow2}1a, transparent 60%)`,
				}}
			/>
			<AbsoluteFill
				style={{
					backgroundImage: `linear-gradient(${C.panelEdge}55 1px, transparent 1px),
            linear-gradient(90deg, ${C.panelEdge}55 1px, transparent 1px)`,
					backgroundSize: '80px 80px',
					backgroundPosition: `0 ${(f * 0.3) % 80}px`,
					maskImage: 'radial-gradient(circle at 50% 50%, black 20%, transparent 75%)',
					WebkitMaskImage: 'radial-gradient(circle at 50% 50%, black 20%, transparent 75%)',
					opacity: 0.5,
				}}
			/>
			<AbsoluteFill style={{opacity: 0.07, mixBlendMode: 'overlay'}}>
				<svg width="100%" height="100%">
					<filter id="grain">
						<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={f % 30} />
					</filter>
					<rect width="100%" height="100%" filter="url(#grain)" />
				</svg>
			</AbsoluteFill>
			<AbsoluteFill
				style={{
					background: 'radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.75) 100%)',
				}}
			/>
		</AbsoluteFill>
	);
};

/** Fade + rise entrance driven by a frame offset. */
export const useRise = (delay: number, duration = 18) => {
	const f = useCurrentFrame();
	const t = interpolate(f - delay, [0, duration], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const eased = 1 - Math.pow(1 - t, 3);
	return {opacity: eased, transform: `translateY(${(1 - eased) * 28}px)`};
};
