/**
 * AuditionPlayer - Audio preview player for arrangement sections.
 *
 * Allows playing, stopping, and looping individual sections with
 * solo/mute controls per role.
 */
import { useState, useRef, useCallback, useEffect } from 'react';
import { ArrangementSection } from '../../api/arrangement';
import { ROLE_COLORS, ROLE_LABELS, StemRole } from '../../api/userLoop';
import './AuditionPlayer.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface AuditionPlayerProps {
  projectId: string;
  sections: ArrangementSection[];
  roles: string[];
  autoPlay?: boolean;
}

export default function AuditionPlayer({
  projectId,
  sections,
  roles,
  autoPlay,
}: AuditionPlayerProps): JSX.Element {
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [looping, setLooping] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [soloRoles, setSoloRoles] = useState<Set<string>>(new Set());
  const [muteRoles, setMuteRoles] = useState<Set<string>>(new Set());
  const [progress, setProgress] = useState(0);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const animFrameRef = useRef<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const autoPlayedRef = useRef(false);

  // Cleanup audio URL on unmount
  useEffect(() => {
    return () => {
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }
      cancelAnimationFrame(animFrameRef.current);
    };
  }, []);

  // Auto-scroll into view and auto-select first section when autoPlay is true
  useEffect(() => {
    if (autoPlay && !autoPlayedRef.current && sections.length > 0) {
      autoPlayedRef.current = true;
      // Scroll player into view
      containerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Auto-select first section
      setSelectedSectionId(sections[0].id);
    }
  }, [autoPlay, sections]);

  const handlePlay = useCallback(async () => {
    if (!selectedSectionId) return;

    setLoading(true);
    setError(null);

    try {
      // Fetch rendered audio
      const body: Record<string, unknown> = { sectionId: selectedSectionId };
      if (soloRoles.size > 0) {
        body.soloRoles = Array.from(soloRoles);
      } else if (muteRoles.size > 0) {
        body.muteRoles = Array.from(muteRoles);
      }

      const response = await fetch(
        `${API_BASE_URL}/api/project/${projectId}/audition`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Audition failed' }));
        throw new Error(err.detail || `Failed with status ${response.status}`);
      }

      const blob = await response.blob();

      // Revoke previous URL
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }

      const url = URL.createObjectURL(blob);
      audioUrlRef.current = url;

      // Create or reuse audio element
      if (!audioRef.current) {
        audioRef.current = new Audio();
      }
      const audio = audioRef.current;
      audio.src = url;
      audio.loop = looping;

      audio.onended = () => {
        if (!looping) {
          setPlaying(false);
          setProgress(0);
        }
      };

      await audio.play();
      setPlaying(true);

      // Update progress
      const updateProgress = () => {
        if (audio.duration > 0) {
          setProgress(audio.currentTime / audio.duration);
        }
        if (!audio.paused) {
          animFrameRef.current = requestAnimationFrame(updateProgress);
        }
      };
      animFrameRef.current = requestAnimationFrame(updateProgress);

    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedSectionId, soloRoles, muteRoles, looping]);

  const handleStop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    cancelAnimationFrame(animFrameRef.current);
    setPlaying(false);
    setProgress(0);
  }, []);

  const toggleSolo = useCallback((role: string) => {
    setSoloRoles((prev) => {
      const next = new Set(prev);
      if (next.has(role)) {
        next.delete(role);
      } else {
        next.add(role);
      }
      return next;
    });
    // Clear mute when soloing
    setMuteRoles(new Set());
  }, []);

  const toggleMute = useCallback((role: string) => {
    setMuteRoles((prev) => {
      const next = new Set(prev);
      if (next.has(role)) {
        next.delete(role);
      } else {
        next.add(role);
      }
      return next;
    });
    // Clear solo when muting
    setSoloRoles(new Set());
  }, []);

  const selectedSection = sections.find((s) => s.id === selectedSectionId);

  return (
    <div className="audition-player" ref={containerRef}>
      <div className="audition-header">
        <span className="audition-title">Section Audition</span>
      </div>

      {/* Section selector */}
      <div className="audition-section-select">
        <label>Section:</label>
        <select
          value={selectedSectionId || ''}
          onChange={(e) => {
            handleStop();
            setSelectedSectionId(e.target.value || null);
          }}
        >
          <option value="">Select a section...</option>
          {sections.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label} ({s.type}, bars {s.startBar}–{s.endBar})
            </option>
          ))}
        </select>
      </div>

      {/* Transport controls */}
      <div className="audition-transport">
        <button
          className="audition-btn play"
          onClick={playing ? handleStop : handlePlay}
          disabled={!selectedSectionId || loading}
        >
          {loading ? 'Loading...' : playing ? 'Stop' : 'Play'}
        </button>
        <button
          className={`audition-btn loop ${looping ? 'active' : ''}`}
          onClick={() => {
            setLooping((v) => !v);
            if (audioRef.current) {
              audioRef.current.loop = !looping;
            }
          }}
          title="Toggle loop"
        >
          Loop
        </button>
        {/* Progress bar */}
        {selectedSectionId && (
          <div className="audition-progress">
            <div
              className="audition-progress-fill"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
        )}
        {selectedSection && (
          <span className="audition-section-info">
            {selectedSection.label} ({(selectedSection.endBar - selectedSection.startBar).toFixed(0)} bars)
          </span>
        )}
      </div>

      {/* Solo/Mute controls */}
      {selectedSectionId && roles.length > 0 && (
        <div className="audition-roles">
          <span className="audition-roles-label">Roles:</span>
          {roles.map((role) => {
            const color = ROLE_COLORS[role as StemRole] || '#9E9E9E';
            const label = ROLE_LABELS[role as StemRole] || role;
            const isSoloed = soloRoles.has(role);
            const isMuted = muteRoles.has(role);

            return (
              <div key={role} className="audition-role-item">
                <span
                  className="audition-role-dot"
                  style={{ backgroundColor: color }}
                />
                <span className="audition-role-name">{label}</span>
                <button
                  className={`audition-role-btn solo ${isSoloed ? 'active' : ''}`}
                  onClick={() => toggleSolo(role)}
                  title={`Solo ${label}`}
                >
                  S
                </button>
                <button
                  className={`audition-role-btn mute ${isMuted ? 'active' : ''}`}
                  onClick={() => toggleMute(role)}
                  title={`Mute ${label}`}
                >
                  M
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="audition-error">
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}
    </div>
  );
}
