import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadMono} from '@remotion/google-fonts/JetBrainsMono';

export const sans = loadInter('normal', {weights: ['400', '500', '700', '800'], subsets: ['latin', 'latin-ext']})
	.fontFamily;
export const mono = loadMono('normal', {weights: ['400', '700'], subsets: ['latin', 'latin-ext']}).fontFamily;

export const C = {
	bg: '#05060a',
	panel: '#0b0e15',
	panelEdge: '#1a2030',
	text: '#e8ebf2',
	mute: '#7d8597',
	faint: '#3a4254',
	anna: '#22d3ee',
	marcel: '#f5a524',
	block: '#f43f5e',
	ok: '#34d399',
	violet: '#8b5cf6',
} as const;

export const FPS = 30;
