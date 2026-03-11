/**
 * SuggestionPanel - Side panel showing variation suggestions (Phase 6C).
 *
 * Displays dismissible suggestion cards with "Apply" / "Dismiss" buttons.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  VariationSuggestion,
  SuggestionsResponse,
  getSuggestions,
  regenerateSuggestions,
  applySuggestion,
  dismissSuggestion,
  SUGGESTION_TYPE_LABELS,
} from '../../api/suggestions';
import { Arrangement } from '../../api/arrangement';
import './SuggestionPanel.css';

interface SuggestionPanelProps {
  projectId: string;
  onArrangementUpdate?: (arrangement: Arrangement) => void;
}

export default function SuggestionPanel({
  projectId,
  onArrangementUpdate,
}: SuggestionPanelProps): JSX.Element {
  const [suggestions, setSuggestions] = useState<VariationSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({ total: 0, applied: 0, dismissed: 0 });

  const loadSuggestions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data: SuggestionsResponse = await getSuggestions(projectId);
      setSuggestions(data.suggestions);
      setStats({ total: data.total, applied: data.applied, dismissed: data.dismissed });
    } catch (err: any) {
      setError(err.message || 'Failed to load suggestions');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadSuggestions();
  }, [loadSuggestions]);

  const handleRegenerate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await regenerateSuggestions(projectId);
      setSuggestions(data.suggestions);
      setStats({ total: data.total, applied: 0, dismissed: 0 });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const handleApply = useCallback(async (suggestionId: string) => {
    try {
      const result = await applySuggestion(projectId, suggestionId);
      setSuggestions((prev) =>
        prev.map((s) => (s.id === suggestionId ? result.suggestion : s)),
      );
      setStats((prev) => ({ ...prev, applied: prev.applied + 1 }));
      if (onArrangementUpdate) {
        onArrangementUpdate(result.arrangement);
      }
    } catch (err: any) {
      setError(err.message);
    }
  }, [projectId, onArrangementUpdate]);

  const handleDismiss = useCallback(async (suggestionId: string) => {
    try {
      const result = await dismissSuggestion(projectId, suggestionId);
      setSuggestions((prev) =>
        prev.map((s) => (s.id === suggestionId ? result.suggestion : s)),
      );
      setStats((prev) => ({ ...prev, dismissed: prev.dismissed + 1 }));
    } catch (err: any) {
      setError(err.message);
    }
  }, [projectId]);

  // Filter to show only pending suggestions
  const pending = suggestions.filter((s) => !s.applied && !s.dismissed);
  const applied = suggestions.filter((s) => s.applied);

  return (
    <div className="sug-panel">
      <div className="sug-panel-header">
        <h3>Suggestions</h3>
        <div className="sug-panel-stats">
          <span className="sug-stat">{pending.length} pending</span>
          <span className="sug-stat applied">{stats.applied} applied</span>
        </div>
        <button
          className="sug-refresh-btn"
          onClick={handleRegenerate}
          disabled={loading}
          title="Regenerate suggestions"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="sug-error">
          {error}
          <button onClick={() => setError(null)}>x</button>
        </div>
      )}

      {loading && <div className="sug-loading">Analyzing arrangement...</div>}

      {!loading && pending.length === 0 && applied.length === 0 && (
        <div className="sug-empty">No suggestions available.</div>
      )}

      <div className="sug-list">
        {pending.map((suggestion) => (
          <SuggestionCard
            key={suggestion.id}
            suggestion={suggestion}
            onApply={() => handleApply(suggestion.id)}
            onDismiss={() => handleDismiss(suggestion.id)}
          />
        ))}

        {applied.length > 0 && (
          <>
            <div className="sug-divider">Applied</div>
            {applied.map((suggestion) => (
              <SuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                onApply={() => {}}
                onDismiss={() => {}}
              />
            ))}
          </>
        )}
      </div>
    </div>
  );
}

interface SuggestionCardProps {
  suggestion: VariationSuggestion;
  onApply: () => void;
  onDismiss: () => void;
}

function SuggestionCard({ suggestion, onApply, onDismiss }: SuggestionCardProps): JSX.Element {
  const typeLabel = SUGGESTION_TYPE_LABELS[suggestion.type] || suggestion.type;
  const isActionable = !suggestion.applied && !suggestion.dismissed;

  return (
    <div className={`sug-card ${suggestion.applied ? 'applied' : ''} ${suggestion.dismissed ? 'dismissed' : ''}`}>
      <div className="sug-card-header">
        <span className={`sug-type-badge type-${suggestion.type}`}>
          {typeLabel}
        </span>
      </div>
      <p className="sug-card-desc">{suggestion.description}</p>
      {isActionable && (
        <div className="sug-card-actions">
          <button className="sug-apply-btn" onClick={onApply}>
            Apply
          </button>
          <button className="sug-dismiss-btn" onClick={onDismiss}>
            Dismiss
          </button>
        </div>
      )}
      {suggestion.applied && (
        <div className="sug-card-status applied">Applied</div>
      )}
    </div>
  );
}
