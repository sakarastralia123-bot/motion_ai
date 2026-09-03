import React from "react";
import {
  AbsoluteFill,
  Composition,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

import graphicsPlan from "./graphicsPlan.json";
import faceSafeZones from "./faceSafeZones.json";


// ============================================================
// TYPES
// ============================================================

type Graphic = {
  speech_start?: number;
  speech_end?: number;

  start?: number;
  end?: number;

  importance?: number;
  concept?: string;
  reason?: string;

  graphic_type?: string;
  type?: string;

  visual_description?: string;
  text?: string;

  position?: string;

  animation_in?: string;
  animation_out?: string;

  animation_duration?: number;
};

type FaceSample = {
  time?: number;
  timestamp?: number;
  safe_positions?: string[];
};


// ============================================================
// STYLE
// ============================================================

const STYLE = {
  dark: "#21152B",
  purple: "#331944",
  accent: "#FF5733",
  accentDark: "#D93E20",
  pink: "#F01090",
  green: "#109040",

  white: "#FFFFFF",
  soft: "#F7F4F1",
  gray: "#77717A",
  lightBorder: "rgba(33,21,43,0.10)",
};


// ============================================================
// LOAD GRAPHICS
// ============================================================

const getGraphics = (): Graphic[] => {
  const data: any = graphicsPlan;

  let graphics: any[] = [];

  if (Array.isArray(data)) {
    graphics = data;
  } else if (Array.isArray(data?.graphics)) {
    graphics = data.graphics;
  } else if (Array.isArray(data?.plan)) {
    graphics = data.plan;
  }

  return graphics
    .map((g: any) => ({
      ...g,
      speech_start:
        typeof g.speech_start === "number"
          ? g.speech_start
          : typeof g.start === "number"
            ? g.start
            : null,

      speech_end:
        typeof g.speech_end === "number"
          ? g.speech_end
          : typeof g.end === "number"
            ? g.end
            : null,
    }))
    .filter(
      (g: any) =>
        Number.isFinite(g.speech_start) &&
        Number.isFinite(g.speech_end) &&
        g.speech_end > g.speech_start &&
        typeof g.text === "string",
    );
};


// ============================================================
// LOAD FACE SAFE ZONES
// ============================================================

const getFaceSamples = (): FaceSample[] => {
  const data: any = faceSafeZones;

  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.samples)) {
    return data.samples;
  }

  if (Array.isArray(data?.face_samples)) {
    return data.face_samples;
  }

  return [];
};


// ============================================================
// FACE SAFE POSITION
// ============================================================

const getSafePosition = (
  desiredPosition: string | undefined,
  time: number,
): string => {
  const samples = getFaceSamples();

  if (samples.length === 0) {
    return desiredPosition || "upper_right";
  }

  let closest = samples[0];
  let closestDistance = Infinity;

  for (const sample of samples) {
    const sampleTime =
      typeof sample.time === "number"
        ? sample.time
        : typeof sample.timestamp === "number"
          ? sample.timestamp
          : 0;

    const distance = Math.abs(sampleTime - time);

    if (distance < closestDistance) {
      closestDistance = distance;
      closest = sample;
    }
  }

  const safePositions =
    Array.isArray(closest.safe_positions)
      ? closest.safe_positions
      : [];

  for (const position of safePositions) {
    if (position === desiredPosition) {
      return position;
    }
  }

  if (safePositions.length > 0) {
    return safePositions[0];
  }

  return desiredPosition || "upper_right";
};


// ============================================================
// POSITION
// ============================================================

const getPositionStyle = (position: string): React.CSSProperties => {
  const common: React.CSSProperties = {
    position: "absolute",
  };

  switch (position) {
    case "upper_left":
      return {
        ...common,
        left: 80,
        top: 100,
      };

    case "upper_right":
      return {
        ...common,
        right: 80,
        top: 100,
      };

    case "middle_left":
      return {
        ...common,
        left: 80,
        top: "50%",
      };

    case "middle_right":
      return {
        ...common,
        right: 80,
        top: "50%",
      };

    case "bottom_left":
      return {
        ...common,
        left: 80,
        bottom: 100,
      };

    case "bottom_right":
      return {
        ...common,
        right: 80,
        bottom: 100,
      };

    default:
      return {
        ...common,
        right: 80,
        top: 100,
      };
  }
};


// ============================================================
// WORD SPLIT
// ============================================================

const AnimatedWords: React.FC<{
  text: string;
  progress: number;
}> = ({ text, progress }) => {
  const words = text.split(" ");

  return (
    <>
      {words.map((word, index) => {
        const delay = index * 0.07;

        const wordProgress = Math.max(
          0,
          Math.min(1, (progress - delay) / 0.35),
        );

        const y = interpolate(
          wordProgress,
          [0, 1],
          [35, 0],
        );

        const opacity = interpolate(
          wordProgress,
          [0, 1],
          [0, 1],
        );

        return (
          <span
            key={`${word}-${index}`}
            style={{
              display: "inline-block",
              marginRight: 14,
              opacity,
              transform: `translateY(${y}px)`,
            }}
          >
            {word}
          </span>
        );
      })}
    </>
  );
};


// ============================================================
// ACCENT LINE
// ============================================================

const AccentLine: React.FC<{
  progress: number;
  width?: number;
}> = ({ progress, width = 160 }) => {
  const scale = interpolate(
    progress,
    [0, 1],
    [0, 1],
  );

  return (
    <div
      style={{
        width,
        height: 8,
        borderRadius: 8,
        background: STYLE.accent,
        transform: `scaleX(${scale})`,
        transformOrigin: "left",
        marginTop: 18,
      }}
    />
  );
};


// ============================================================
// KINETIC HEADLINE
// ============================================================

const KineticHeadline: React.FC<{
  text: string;
  progress: number;
}> = ({ text, progress }) => {
  return (
    <div
      style={{
        width: 650,
        padding: "34px 40px",
        background: "rgba(255,255,255,0.96)",
        borderRadius: 28,
        border: `1px solid ${STYLE.lightBorder}`,
        boxShadow:
          "0 25px 70px rgba(33,21,43,0.18)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          fontSize: 22,
          fontWeight: 800,
          letterSpacing: 4,
          color: STYLE.accent,
          marginBottom: 15,
        }}
      >
        KEY IDEA
      </div>

      <div
        style={{
          fontSize: 58,
          lineHeight: 1.02,
          fontWeight: 900,
          color: STYLE.dark,
          letterSpacing: -2,
        }}
      >
        <AnimatedWords
          text={text}
          progress={progress}
        />
      </div>

      <AccentLine progress={progress} />

      <div
        style={{
          position: "absolute",
          right: -30,
          bottom: -30,
          width: 120,
          height: 120,
          borderRadius: "50%",
          background: STYLE.accent,
          opacity: 0.12,
        }}
      />
    </div>
  );
};


// ============================================================
// LARGE NUMBER
// ============================================================

const LargeNumber: React.FC<{
  text: string;
  progress: number;
}> = ({ text, progress }) => {
  const scale = interpolate(
    progress,
    [0, 1],
    [0.6, 1],
  );

  return (
    <div
      style={{
        width: 600,
        padding: 40,
        background: STYLE.dark,
        borderRadius: 32,
        boxShadow:
          "0 30px 80px rgba(0,0,0,0.28)",
        transform: `scale(${scale})`,
      }}
    >
      <div
        style={{
          fontSize: 24,
          color: STYLE.accent,
          fontWeight: 800,
          letterSpacing: 4,
        }}
      >
        IMPORTANT
      </div>

      <div
        style={{
          marginTop: 8,
          fontSize: 90,
          fontWeight: 950,
          color: STYLE.white,
          lineHeight: 1,
        }}
      >
        {text}
      </div>

      <div
        style={{
          height: 5,
          width: 220,
          background: STYLE.accent,
          marginTop: 22,
        }}
      />
    </div>
  );
};


// ============================================================
// PROCESS GRAPHIC
// ============================================================

const ProcessGraphic: React.FC<{
  progress: number;
}> = ({ progress }) => {
  const steps = [
    "IDEA",
    "RESEARCH",
    "ORGANIZE",
    "WRITE",
  ];

  return (
    <div
      style={{
        width: 760,
        padding: 35,
        borderRadius: 30,
        background: "rgba(255,255,255,0.97)",
        boxShadow:
          "0 25px 80px rgba(33,21,43,0.18)",
        border:
          `1px solid ${STYLE.lightBorder}`,
      }}
    >
      <div
        style={{
          fontSize: 22,
          fontWeight: 900,
          letterSpacing: 5,
          color: STYLE.accent,
        }}
      >
        THE PROCESS
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          marginTop: 32,
        }}
      >
        {steps.map((step, index) => {
          const delay = index * 0.18;

          const p = Math.max(
            0,
            Math.min(1, (progress - delay) / 0.35),
          );

          const scale = interpolate(
            p,
            [0, 1],
            [0.5, 1],
          );

          const opacity = interpolate(
            p,
            [0, 1],
            [0, 1],
          );

          return (
            <React.Fragment key={step}>
              <div
                style={{
                  width: 120,
                  height: 120,
                  borderRadius: "50%",
                  background:
                    index === 0
                      ? STYLE.accent
                      : STYLE.soft,
                  border:
                    `4px solid ${
                      index === 0
                        ? STYLE.accent
                        : STYLE.purple
                    }`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  textAlign: "center",
                  fontSize: 17,
                  fontWeight: 900,
                  color:
                    index === 0
                      ? STYLE.white
                      : STYLE.dark,
                  transform: `scale(${scale})`,
                  opacity,
                }}
              >
                {step}
              </div>

              {index < steps.length - 1 && (
                <div
                  style={{
                    width: 55,
                    height: 5,
                    background: STYLE.purple,
                    opacity: p,
                  }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};


// ============================================================
// BRAINSTORMING GRAPHIC
// ============================================================

const BrainstormGraphic: React.FC<{
  progress: number;
}> = ({ progress }) => {
  const ideas = [
    "IDEA",
    "QUESTION",
    "EVIDENCE",
    "TOPIC",
  ];

  return (
    <div
      style={{
        width: 650,
        height: 430,
        position: "relative",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          transform:
            `translate(-50%, -50%) scale(${
              interpolate(progress, [0, 1], [0.6, 1])
            })`,
          width: 190,
          height: 190,
          borderRadius: "50%",
          background: STYLE.dark,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: STYLE.white,
          fontSize: 28,
          fontWeight: 900,
          boxShadow:
            "0 25px 70px rgba(33,21,43,0.25)",
        }}
      >
        BRAINSTORM
      </div>

      {ideas.map((idea, index) => {
        const angle =
          (index / ideas.length) * Math.PI * 2 -
          Math.PI / 2;

        const radius = 180;

        const x =
          Math.cos(angle) * radius;

        const y =
          Math.sin(angle) * radius;

        const delay = index * 0.15;

        const p = Math.max(
          0,
          Math.min(1, (progress - delay) / 0.4),
        );

        const scale = interpolate(
          p,
          [0, 1],
          [0, 1],
        );

        return (
          <div
            key={idea}
            style={{
              position: "absolute",
              left: "50%",
              top: "50%",
              transform:
                `translate(calc(-50% + ${x}px), calc(-50% + ${y}px)) scale(${scale})`,
              padding: "16px 25px",
              borderRadius: 20,
              background: STYLE.white,
              border:
                `2px solid ${STYLE.accent}`,
              fontSize: 18,
              fontWeight: 900,
              color: STYLE.dark,
              boxShadow:
                "0 15px 40px rgba(33,21,43,0.15)",
            }}
          >
            {idea}
          </div>
        );
      })}
    </div>
  );
};


// ============================================================
// DOCUMENT STACK
// ============================================================

const DocumentGraphic: React.FC<{
  text: string;
  progress: number;
}> = ({ text, progress }) => {
  const cards = [
    "RESEARCH",
    "SOURCES",
    "PROPOSAL",
  ];

  return (
    <div
      style={{
        width: 620,
        height: 440,
        position: "relative",
      }}
    >
      {cards.map((card, index) => {
        const delay = index * 0.15;

        const p = Math.max(
          0,
          Math.min(1, (progress - delay) / 0.45),
        );

        const y = interpolate(
          p,
          [0, 1],
          [100, index * 35],
        );

        const rotate = interpolate(
          p,
          [0, 1],
          [index === 1 ? -8 : 8, index === 1 ? -4 : 4],
        );

        return (
          <div
            key={card}
            style={{
              position: "absolute",
              left: 60 + index * 35,
              top: 40 + index * 25,
              width: 440,
              height: 280,
              background: STYLE.white,
              borderRadius: 25,
              border:
                `1px solid ${STYLE.lightBorder}`,
              boxShadow:
                "0 25px 60px rgba(33,21,43,0.18)",
              transform:
                `translateY(${y}px) rotate(${rotate}deg)`,
              padding: 30,
            }}
          >
            <div
              style={{
                width: 90,
                height: 10,
                borderRadius: 5,
                background: STYLE.accent,
              }}
            />

            <div
              style={{
                marginTop: 30,
                fontSize: 34,
                fontWeight: 900,
                color: STYLE.dark,
              }}
            >
              {card}
            </div>

            <div
              style={{
                marginTop: 25,
                width: "75%",
                height: 10,
                background: STYLE.soft,
                borderRadius: 5,
              }}
            />

            <div
              style={{
                marginTop: 12,
                width: "55%",
                height: 10,
                background: STYLE.soft,
                borderRadius: 5,
              }}
            />
          </div>
        );
      })}

      <div
        style={{
          position: "absolute",
          bottom: 10,
          left: 80,
          fontSize: 24,
          fontWeight: 900,
          color: STYLE.accent,
        }}
      >
        {text}
      </div>
    </div>
  );
};


// ============================================================
// AUDIENCE GRAPHIC
// ============================================================

const AudienceGraphic: React.FC<{
  progress: number;
}> = ({ progress }) => {
  return (
    <div
      style={{
        width: 650,
        padding: 40,
        borderRadius: 30,
        background: STYLE.dark,
        boxShadow:
          "0 30px 80px rgba(0,0,0,0.25)",
      }}
    >
      <div
        style={{
          textAlign: "center",
          fontSize: 25,
          fontWeight: 900,
          color: STYLE.accent,
          letterSpacing: 4,
        }}
      >
        AUDIENCE
      </div>

      <div
        style={{
          marginTop: 40,
          display: "flex",
          justifyContent: "center",
          gap: 25,
        }}
      >
        {[0, 1, 2, 3, 4].map((i) => {
          const p = Math.max(
            0,
            Math.min(1, (progress - i * 0.08) / 0.35),
          );

          const scale = interpolate(
            p,
            [0, 1],
            [0.4, 1],
          );

          return (
            <div
              key={i}
              style={{
                width: 75,
                height: 75,
                borderRadius: "50%",
                background:
                  i === 2
                    ? STYLE.accent
                    : STYLE.white,
                transform: `scale(${scale})`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 28,
              }}
            >
              ●
            </div>
          );
        })}
      </div>
    </div>
  );
};


// ============================================================
// ARGUMENT GRAPHIC
// ============================================================

const ArgumentGraphic: React.FC<{
  progress: number;
}> = ({ progress }) => {
  return (
    <div
      style={{
        width: 720,
        padding: 35,
        borderRadius: 30,
        background: STYLE.white,
        boxShadow:
          "0 25px 70px rgba(33,21,43,0.20)",
      }}
    >
      <div
        style={{
          fontSize: 22,
          fontWeight: 900,
          color: STYLE.accent,
          letterSpacing: 4,
        }}
      >
        BUILD THE ARGUMENT
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 20,
          marginTop: 30,
        }}
      >
        <ArgumentBox
          label="CLAIM"
          progress={progress}
        />

        <Arrow progress={progress} />

        <ArgumentBox
          label="EVIDENCE"
          progress={progress}
        />

        <Arrow progress={progress} />

        <ArgumentBox
          label="ARGUMENT"
          progress={progress}
          highlight
        />
      </div>
    </div>
  );
};


const ArgumentBox: React.FC<{
  label: string;
  progress: number;
  highlight?: boolean;
}> = ({ label, progress, highlight }) => {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 130,
        height: 110,
        borderRadius: 20,
        background:
          highlight
            ? STYLE.dark
            : STYLE.soft,
        color:
          highlight
            ? STYLE.white
            : STYLE.dark,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 18,
        fontWeight: 900,
        transform:
          `scale(${interpolate(
            progress,
            [0, 1],
            [0.85, 1],
          )})`,
      }}
    >
      {label}
    </div>
  );
};


const Arrow: React.FC<{
  progress: number;
}> = ({ progress }) => {
  return (
    <div
      style={{
        fontSize: 40,
        fontWeight: 900,
        color: STYLE.accent,
        opacity: progress,
      }}
    >
      →
    </div>
  );
};


// ============================================================
// GENERIC GRAPHIC
// ============================================================

const GenericGraphic: React.FC<{
  text: string;
  concept: string;
  progress: number;
}> = ({ text, concept, progress }) => {
  return (
    <KineticHeadline
      text={text || concept.toUpperCase()}
      progress={progress}
    />
  );
};


// ============================================================
// CHOOSE VISUAL
// ============================================================

const renderVisual = (
  graphic: Graphic,
  progress: number,
) => {
  const type =
    (
      graphic.graphic_type ||
      graphic.type ||
      ""
    ).toLowerCase();

  const concept =
    (
      graphic.concept ||
      ""
    ).toLowerCase();

  const text =
    graphic.text ||
    concept.toUpperCase();

  // PROCESS
  if (
    type.includes("process") ||
    concept.includes("process")
  ) {
    return (
      <ProcessGraphic
        progress={progress}
      />
    );
  }

  // BRAINSTORMING
  if (
    concept.includes("brainstorm") ||
    text.toLowerCase().includes("brainstorm")
  ) {
    return (
      <BrainstormGraphic
        progress={progress}
      />
    );
  }

  // DOCUMENT / SOURCES / PROPOSAL
  if (
    concept.includes("proposal") ||
    concept.includes("bibliography") ||
    concept.includes("source") ||
    concept.includes("outline") ||
    concept.includes("research")
  ) {
    return (
      <DocumentGraphic
        text={text}
        progress={progress}
      />
    );
  }

  // AUDIENCE
  if (
    concept.includes("audience")
  ) {
    return (
      <AudienceGraphic
        progress={progress}
      />
    );
  }

  // ARGUMENT
  if (
    concept.includes("argument") ||
    concept.includes("claim") ||
    concept.includes("evidence")
  ) {
    return (
      <ArgumentGraphic
        progress={progress}
      />
    );
  }

  // NUMBERS
  if (
    type.includes("number") ||
    type.includes("stat") ||
    /\d/.test(text)
  ) {
    return (
      <LargeNumber
        text={text}
        progress={progress}
      />
    );
  }

  // DEFAULT
  return (
    <GenericGraphic
      text={text}
      concept={concept}
      progress={progress}
    />
  );
};


// ============================================================
// ONE ANIMATED GRAPHIC
// ============================================================

const AnimatedGraphic: React.FC<{
  graphic: Graphic;
}> = ({ graphic }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const start =
    typeof graphic.speech_start === "number"
      ? graphic.speech_start
      : 0;

  const end =
    typeof graphic.speech_end === "number"
      ? graphic.speech_end
      : start + 2;

  const startFrame = Math.round(start * fps);
  const endFrame = Math.round(end * fps);

  if (
    !Number.isFinite(startFrame) ||
    !Number.isFinite(endFrame) ||
    endFrame <= startFrame
  ) {
    return null;
  }

  if (
    frame < startFrame ||
    frame > endFrame
  ) {
    return null;
  }

  const localFrame =
    frame - startFrame;

  const duration =
    endFrame - startFrame;

  // ----------------------------------------
  // ENTRANCE
  // ----------------------------------------

  const entrance =
    spring({
      frame: localFrame,
      fps,
      config: {
        damping: 14,
        stiffness: 120,
        mass: 0.7,
      },
    });

  // ----------------------------------------
  // EXIT
  // ----------------------------------------

  const exitFrames =
    Math.min(
      15,
      Math.max(
        8,
        Math.floor(duration * 0.18),
      ),
    );

  const exitStart =
    Math.max(
      0,
      duration - exitFrames,
    );

  const exit =
    interpolate(
      localFrame,
      [
        exitStart,
        duration,
      ],
      [1, 0],
      {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      },
    );

  // ----------------------------------------
  // MOVEMENT
  // ----------------------------------------

  const y =
    interpolate(
      entrance,
      [0, 1],
      [70, 0],
    );

  const scale =
    interpolate(
      entrance,
      [0, 1],
      [0.90, 1],
    );

  const opacity =
    entrance * exit;

  const desiredPosition =
    graphic.position ||
    "upper_right";

  const safePosition =
    getSafePosition(
      desiredPosition,
      start,
    );

  const positionStyle =
    getPositionStyle(
      safePosition,
    );

  const transform =
    safePosition === "middle_left" ||
    safePosition === "middle_right"
      ? `translateY(-50%) translateY(${y}px) scale(${scale})`
      : `translateY(${y}px) scale(${scale})`;

  return (
    <div
      style={{
        ...positionStyle,
        opacity,
        transform,
        zIndex: 20,
      }}
    >
      {renderVisual(
        graphic,
        entrance,
      )}
    </div>
  );
};


// ============================================================
// MOTION GRAPHICS ENGINE
// ============================================================

const MotionGraphics: React.FC = () => {
  const graphics =
    getGraphics();

  return (
    <>
      {graphics.map(
        (graphic, index) => (
          <AnimatedGraphic
            key={`${graphic.text}-${index}`}
            graphic={graphic}
          />
        ),
      )}
    </>
  );
};


// ============================================================
// MAIN VIDEO
// ============================================================

export const MyComponent: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        background: "#000",
      }}
    >
      <OffthreadVideo
        src={staticFile("Video.mp4")}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />

      <MotionGraphics />
    </AbsoluteFill>
  );
};


// ============================================================
// COMPOSITION
// ============================================================

export const MyComposition = () => {
  return (
    <Composition
      id="MyComp"
      component={MyComponent}
      durationInFrames={1820}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};