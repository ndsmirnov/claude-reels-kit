import React from 'react';
import {Composition} from 'remotion';
import {Overlay, OverlayProps} from './Overlay';

// Прозрачный слой графики 1080×1920 поверх рилса. Длительность и элементы — из --props (json).
export const Root: React.FC = () => (
  <Composition
    id="Overlay"
    component={Overlay}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={150}
    defaultProps={{duration: 5, items: []} as OverlayProps}
    calculateMetadata={({props}) => ({durationInFrames: Math.max(1, Math.round(props.duration * 30))})}
  />
);
