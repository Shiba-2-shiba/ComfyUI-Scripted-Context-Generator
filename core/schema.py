from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
import json

@dataclass
class MetaInfo:
    """Metadata for the prompt context, affecting style and mood."""
    mood: str = ""
    style: str = ""
    tags: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetaInfo':
        return cls(
            mood=str(data.get("mood", "")),
            style=str(data.get("style", "")),
            tags=data.get("tags", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class DebugInfo:
    """Diagnostic information for tracing generation decisions."""
    node: str
    seed: int
    decision: Dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PromptContext:
    """Core context object to be passed between nodes."""
    subj: str = ""
    costume: str = ""
    loc: str = ""
    action: str = ""
    meta: MetaInfo = field(default_factory=MetaInfo)
    
    # Extra fields for flexibility (like 'garnish')
    extras: Dict[str, Any] = field(default_factory=dict)
    
    # Traceability
    history: list[DebugInfo] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], strict: bool = False) -> 'PromptContext':
        """
        Create PromptContext from dictionary.
        
        Args:
            data: Input dictionary.
            strict: If True, raises validation errors for missing keys (future use).
        """
        meta_data = data.get("meta", {})
        if not isinstance(meta_data, dict):
            meta_data = {}
            
        # Parse history if present
        history_data = data.get("history", [])
        history = []
        if isinstance(history_data, list):
            for h in history_data:
                if isinstance(h, dict):
                    history.append(DebugInfo(
                        node=h.get("node", "unknown"),
                        seed=h.get("seed", 0),
                        decision=h.get("decision", {}),
                        warnings=h.get("warnings", [])
                    ))
            
        return cls(
            subj=str(data.get("subj", "")),
            costume=str(data.get("costume", "")),
            loc=str(data.get("loc", "")),
            action=str(data.get("action", "")),
            meta=MetaInfo.from_dict(meta_data),
            extras=data.get("extras", {}),
            history=history
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'PromptContext':
        """Parse from JSON string."""
        if not json_str or json_str.strip() == "":
            return cls()
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError:
            # Fallback or error? For robust nodes, maybe return empty with warning?
            # Phase 2 will add debug_info to track this.
            return cls()
