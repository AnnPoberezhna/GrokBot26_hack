import React from 'react';
import {Composition} from 'remotion';
import {Film, TOTAL_FRAMES} from './Film';
import {KANZEN_TOTAL, KanzenFilm} from './kanzen/Kanzen';
import {FPS} from './theme';

export const RemotionRoot: React.FC = () => (
	<>
		<Composition id="GrokMesh" component={Film} durationInFrames={TOTAL_FRAMES} fps={FPS} width={1920} height={1080} />
		<Composition
			id="GrokMeshKanzen"
			component={KanzenFilm}
			durationInFrames={KANZEN_TOTAL}
			fps={FPS}
			width={1920}
			height={1080}
		/>
	</>
);
