import { useEffect } from "react";

export interface LightboxImage {
  src: string;
  label: string;
}

export function Lightbox({
  images,
  index,
  onClose,
  onNavigate,
}: {
  images: LightboxImage[];
  index: number;
  onClose: () => void;
  onNavigate: (index: number) => void;
}) {
  const hasPrev = index > 0;
  const hasNext = index < images.length - 1;

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft" && index > 0) onNavigate(index - 1);
      else if (e.key === "ArrowRight" && index < images.length - 1) onNavigate(index + 1);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [index, images.length, onClose, onNavigate]);

  const current = images[index];
  if (!current) return null;

  return (
    <div className="lightbox-backdrop" onClick={onClose}>
      <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
        <div className="lightbox-header">
          <span className="mono text-muted">{current.label}</span>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>
            Close ✕
          </button>
        </div>
        <div className="lightbox-image-wrap">
          <img src={current.src} alt={current.label} className="lightbox-image" />
        </div>
        <div className="lightbox-nav">
          <button className="btn btn-sm" onClick={() => hasPrev && onNavigate(index - 1)} disabled={!hasPrev}>
            ← Previous
          </button>
          <span className="text-faint mono">
            {index + 1} / {images.length}
          </span>
          <button className="btn btn-sm" onClick={() => hasNext && onNavigate(index + 1)} disabled={!hasNext}>
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}
