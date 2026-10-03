import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, continueRender, delayRender, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// Элементы графики (рефы Инсты 02.10.2026, `_форматы-рилсов.md`). Фирменный шрифт — Montserrat (как в подкасте).
//  shot   — Ф2: скрин всплывает поверх видео В НИЖНЕЙ части кадра (лицо не закрываем), {src, start, end, bottom?, w?}
//  thesis — Ф2: тезис сверху; тезисы подряд сменяются без зазора (иначе текст «моргает»), {text, start, end, y?}
//  logo   — Ф2/Ф3: логотип с мягкой тенью, без подложки, над головой + оценка «7/10», {src, start, end, score?, y?, x?}
//  insert — Ф4: вставка на весь кадр, вход/выход короткой вспышкой, {src, start, end, from?}.
//           Реальная съёмка — ВСЕГДА видео (src .mp4/.mov, from = секунда исходника; render.sh режет кусок) — ОС 02.10: стоп-кадр из видео выглядит мёртво.
//           Картинка (jpg/png) — только для ИИ-генерации, с медленным наездом 1.0→1.08.
//  half   — «Конторка» на пол-экрана: картинка/видео сверху (0…960 px), автор (видео-база) остаётся снизу, жёсткая склейка, {src, start, end, from?, punch?}
//  move (insert/half, картинки): 'in' наезд | 'out' отъезд | 'pan-l'/'pan-r' проход | 'to' наезд к точке fx,fy (0…1, напр. лицо) — ОС 02.10: «картинки оживлять»
//  wobble: true — лёгкое покачивание камеры «как в катсцене старой игры»
//  punch: true (insert/half) — на середине кадра резкий наезд ×1.35 (как в рефе Dd1PxtUOvec)
//  sticker— Ф4: вырезанный персонаж/объект (PNG с прозрачностью) выскакивает поверх видео и слегка покачивается, {src, start, end, x, y, h?}
type Base = {start: number; end: number};
export type Item =
  | (Base & {type: 'shot'; src: string; w?: number; bottom?: number})
  | (Base & {type: 'thesis'; text: string; y?: number})
  | (Base & {type: 'logo'; src: string; score?: string; y?: number; x?: number})
  | (Base & {type: 'insert'; src: string; from?: number; punch?: boolean} & Motion)
  | (Base & {type: 'half'; src: string; from?: number; punch?: boolean; h?: number} & Motion) // h — высота верхней части (03.10: диптих 1312 + подкаст 16:9 снизу 608)
  | (Base & {type: 'sticker'; src: string; x: number; y: number; h?: number});
type Motion = {move?: 'in' | 'out' | 'pan-l' | 'pan-r' | 'to'; fx?: number; fy?: number; wobble?: boolean;
  fit?: 'cover' | 'contain'; py?: number; pz?: number}; // 03.10: fit contain — картинка целиком на размытом фоне (лица не режутся); py — какая часть по высоте видна в half (0 верх…1 низ); pz — сила punch
export type OverlayProps = {duration: number; items: Item[]};

const FONT = 'Montserrat';
const OUT = 6; // кадров на исчезновение
const SHADOW = 'drop-shadow(0 18px 40px rgba(0,0,0,0.45)) drop-shadow(0 4px 10px rgba(0,0,0,0.35))';
const TEXT_SHADOW = '0 4px 10px rgba(0,0,0,0.85), 0 2px 3px rgba(0,0,0,0.75), 0 0 28px rgba(0,0,0,0.5)'; // плотная тень под шрифтом (ОС 02.10)

const useFonts = () => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const faces = [['Medium', 500], ['SemiBold', 600], ['Bold', 700], ['ExtraBold', 800]].map(
      ([n, w]) => new FontFace(FONT, `url(${staticFile(`fonts/Montserrat-${n}.ttf`)})`, {weight: String(w)}));
    Promise.all(faces.map((f) => f.load())).then((l) => {l.forEach((f) => document.fonts.add(f)); continueRender(h);});
  }, [h]);
};

// in/out = анимировать ли появление/исчезновение (для цепочки тезисов — нет)
const useAppear = (start: number, end: number, inAnim = true, outAnim = true) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = Math.round(start * fps), e = Math.round(end * fps);
  if (frame < s || frame >= e) return null;
  const inn = inAnim ? spring({frame: frame - s, fps, config: {damping: 14, stiffness: 180, mass: 0.6}}) : 1;
  const out = outAnim ? interpolate(frame, [e - OUT, e], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  return {scale: (0.82 + 0.18 * inn) * (0.9 + 0.1 * out), opacity: Math.min(inn * 1.4, 1) * out};
};

const Shot: React.FC<{it: Extract<Item, {type: 'shot'}>}> = ({it}) => {
  const a = useAppear(it.start, it.end);
  if (!a) return null;
  const w = (it.w ?? 0.6) * 1080;
  return (
    <div style={{position: 'absolute', left: (1080 - w) / 2, bottom: it.bottom ?? 170, width: w,
      transform: `scale(${a.scale})`, opacity: a.opacity, transformOrigin: '50% 100%', filter: SHADOW}}>
      <Img src={staticFile(it.src)} style={{width: '100%', borderRadius: 28, display: 'block'}} />
    </div>
  );
};

const Thesis: React.FC<{it: Extract<Item, {type: 'thesis'}>; chainIn: boolean; chainOut: boolean}> = ({it, chainIn, chainOut}) => {
  const a = useAppear(it.start, it.end, !chainIn, !chainOut);
  if (!a) return null;
  return (
    <div style={{position: 'absolute', top: it.y ?? 150, left: 80, right: 80, textAlign: 'center',
      fontFamily: FONT, fontWeight: 600, fontSize: 56, lineHeight: 1.18, color: 'white',
      textShadow: TEXT_SHADOW, opacity: a.opacity}}>
      {it.text}
    </div>
  );
};

const Logo: React.FC<{it: Extract<Item, {type: 'logo'}>}> = ({it}) => {
  const a = useAppear(it.start, it.end);
  if (!a) return null;
  return (
    <div style={{position: 'absolute', top: it.y ?? 330, left: it.x ?? 80, display: 'flex', alignItems: 'center', gap: 24,
      transform: `scale(${a.scale})`, opacity: a.opacity, transformOrigin: '0% 50%'}}>
      <Img src={staticFile(it.src)} style={{height: 240, width: 'auto', filter: SHADOW}} />
      {it.score && (
        <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 110, color: 'white', textShadow: TEXT_SHADOW}}>{it.score}</div>
      )}
    </div>
  );
};

const Insert: React.FC<{it: Extract<Item, {type: 'insert' | 'half'}>}> = ({it}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = Math.round(it.start * fps), e = Math.round(it.end * fps);
  if (frame < s || frame >= e) return null;
  const half = it.type === 'half';
  const p = interpolate(frame, [s, e], [0, 1]);
  const mv = it.move ?? 'in';
  let zoom = mv === 'out' ? 1.14 - 0.12 * p : mv === 'to' ? 1 + 0.35 * p : mv.startsWith('pan') ? 1.12 : 1 + (half ? 0.06 : 0.1) * p;
  let tx = mv === 'pan-l' ? 40 - 80 * p : mv === 'pan-r' ? -40 + 80 * p : 0, ty = 0;
  const origin = it.fx !== undefined || it.fy !== undefined ? `${(it.fx ?? 0.5) * 100}% ${(it.fy ?? 0.35) * 100}%` : '50% 35%';
  if (it.punch && frame >= (s + e) / 2) zoom *= it.pz ?? 1.35;
  const contain = it.fit === 'contain';
  const pos = `50% ${(it.py ?? 0.5) * 100}%`;
  if (it.wobble) { tx += Math.sin(frame / 11) * 5 + Math.sin(frame / 4.7) * 1.5; ty += Math.cos(frame / 13) * 4; }
  const flash = Math.max(interpolate(frame, [s, s + 4], [0.55, 0], {extrapolateRight: 'clamp'}),
    interpolate(frame, [e - 3, e], [0, 0.4], {extrapolateLeft: 'clamp'}));
  return (
    <AbsoluteFill style={half ? {height: it.h ?? 960, overflow: 'hidden'} : undefined}>
      {/\.(mp4|mov)$/i.test(it.src) ? (
        <Sequence from={s} durationInFrames={e - s} layout="none">
          <OffthreadVideo src={staticFile(it.src)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </Sequence>
      ) : (
        <>
          {contain && <Img src={staticFile(it.src)} style={{position: 'absolute', width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(28px) brightness(0.7)', transform: 'scale(1.15)'}} />}
          <Img src={staticFile(it.src)} style={{position: 'absolute', width: '100%', height: '100%', objectFit: contain ? 'contain' : 'cover', objectPosition: pos, transform: `translate(${tx}px, ${ty}px) scale(${zoom})`, transformOrigin: origin}} />
        </>
      )}
      <AbsoluteFill style={{backgroundColor: 'white', opacity: flash}} />
    </AbsoluteFill>
  );
};

const Sticker: React.FC<{it: Extract<Item, {type: 'sticker'}>}> = ({it}) => {
  const a = useAppear(it.start, it.end);
  const frame = useCurrentFrame();
  if (!a) return null;
  const bob = Math.sin(frame / 9) * 6; // лёгкое покачивание, чтобы стикер «жил»
  return (
    <Img src={staticFile(it.src)} style={{position: 'absolute', left: it.x, top: it.y + bob, height: it.h ?? 360, width: 'auto',
      transform: `scale(${a.scale})`, opacity: a.opacity, transformOrigin: '50% 100%', filter: SHADOW}} />
  );
};

export const Overlay: React.FC<OverlayProps> = ({items}) => {
  useFonts();
  const th = items.filter((i) => i.type === 'thesis');
  const near = (a: number, b: number) => Math.abs(a - b) < 0.4;
  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      {items.map((it, i) => {
        if (it.type === 'shot') return <Shot key={i} it={it} />;
        if (it.type === 'logo') return <Logo key={i} it={it} />;
        if (it.type === 'insert' || it.type === 'half') return <Insert key={i} it={it} />;
        if (it.type === 'sticker') return <Sticker key={i} it={it} />;
        const next = th.find((o) => o !== it && near(o.start, it.end));
        const prev = th.find((o) => o !== it && near(o.end, it.start));
        // цепочка: текущий тезис держится до начала следующего, смена — мгновенная
        return <Thesis key={i} it={next ? {...it, end: next.start} : it} chainIn={!!prev} chainOut={!!next} />;
      })}
    </AbsoluteFill>
  );
};
