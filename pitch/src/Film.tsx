import React from 'react';
import {linearTiming, TransitionSeries} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {ColdOpen, Close, Demo, DEMO_FRAMES, Graph, Outcome, Problem, Title} from './scenes';

const T = 15;
export const SCENES: [React.FC, number][] = [
	[ColdOpen, 150],
	[Problem, 270],
	[Title, 150],
	[Graph, 270],
	[Demo, DEMO_FRAMES],
	[Outcome, 180],
	[Close, 150],
];
export const TOTAL_FRAMES = SCENES.reduce((a, [, d]) => a + d, 0) - T * (SCENES.length - 1);

export const Film: React.FC = () => (
	<TransitionSeries>
		{SCENES.map(([Scene, duration], i) => (
			<React.Fragment key={i}>
				{i > 0 ? (
					<TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: T})} />
				) : null}
				<TransitionSeries.Sequence durationInFrames={duration}>
					<Scene />
				</TransitionSeries.Sequence>
			</React.Fragment>
		))}
	</TransitionSeries>
);
