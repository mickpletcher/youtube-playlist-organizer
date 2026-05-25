from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_RULES_CONFIG_PATHS = [
    "config/playlist-rules.json",
    "config/playlist-rules.yaml",
    "config/playlist-rules.yml",
]

DEFAULT_RULES_CONFIG = {
    "privacy_defaults": {
        "created_playlist_privacy": "private",
    },
    "keep_rules": {
        "preferred_playlist_titles": ["favorites"],
        "preferred_privacy_order": ["private", "unlisted", "public"],
    },
    "playlist_merge_preferences": {
        "prefer_private_target": True,
        "canonical_playlist_strategy": "largest_first",
    },
    "category_suggestion_filters": {
        "source_playlist_allowlist": [],
        "source_playlist_blocklist": [],
        "target_playlist_allowlist": [],
        "target_playlist_blocklist": [],
    },
    "liked_video_review": {
        "enabled": True,
        "liked_playlist_titles": ["Liked videos", "Liked Videos"],
        "self_image_flag_rules": [
            {
                "keyword_sets": [["looksmax"], ["looksmaxxing"]],
                "reason": "Looksmax style content can reinforce appearance fixation.",
                "severity": "high",
            },
            {
                "keyword_sets": [["alpha male"], ["high value man"], ["sigma male"]],
                "reason": "Status or dominance framing may push self worth into external labels.",
                "severity": "medium",
            },
            {
                "keyword_sets": [["face rating"], ["attractive"], ["ugly"]],
                "reason": "Appearance ranking content can be rough on self image.",
                "severity": "medium",
            },
            {
                "keyword_sets": [["glow up"], ["masculinity"], ["women only want"]],
                "reason": "Identity or desirability framing may be worth reviewing.",
                "severity": "low",
            },
        ],
    },
    "playlist_aliases": {
        "rving": "rv",
        "recipes": "recipe",
        "workouts": "workout",
        "trainings": "training",
        "gamings": "gaming",
    },
    "token_aliases": {
        "rving": "rv",
        "recipes": "recipe",
        "workouts": "workout",
        "trainings": "training",
    },
    "category_rules": [
        {
            "source_playlists": ["AI", "Tech"],
            "target_playlist": "GitHub",
            "keyword_sets": [
                ["github"],
                ["copilot"],
                ["spec-driven"],
                ["spec driven"],
                ["/spec"],
                ["claude code"],
            ],
            "reason": "GitHub and coding workflow content should live in GitHub.",
        },
        {
            "source_playlists": ["AI", "Tech"],
            "target_playlist": "ChatGPT",
            "keyword_sets": [
                ["chatgpt"],
                ["openai"],
                ["custom gpt"],
                ["gpt"],
            ],
            "reason": "ChatGPT and OpenAI content should live in ChatGPT.",
        },
        {
            "source_playlists": ["AI", "Tech"],
            "target_playlist": "Prompt Engineering",
            "keyword_sets": [
                ["prompt"],
                ["prompts"],
            ],
            "reason": "Prompt specific content should live in Prompt Engineering.",
        },
        {
            "source_playlists": ["DIY"],
            "target_playlist": "Solar",
            "keyword_sets": [
                ["solar"],
                ["battery"],
                ["inverter"],
                ["off-grid"],
            ],
            "reason": "Solar system content should live in Solar.",
        },
        {
            "source_playlists": ["DIY"],
            "target_playlist": "Metal Fabrication",
            "keyword_sets": [
                ["weld"],
                ["welding"],
                ["fabrication"],
                ["metal"],
            ],
            "reason": "Metalwork content should live in Metal Fabrication.",
        },
        {
            "source_playlists": ["DIY"],
            "target_playlist": "Woodworking",
            "keyword_sets": [
                ["woodworking"],
                ["wood"],
                ["cabinet"],
            ],
            "reason": "Woodworking content should live in Woodworking.",
        },
        {
            "source_playlists": ["DIY"],
            "target_playlist": "DIY Closet",
            "keyword_sets": [
                ["closet"],
            ],
            "reason": "Closet build content should live in DIY Closet.",
        },
    ],
}


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def normalize_key(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return normalize_space(cleaned)


def singularize_token(token: str) -> str:
    if len(token) <= 3:
        return token
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("ses") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def load_rules_config(config_path: str | None = None) -> dict[str, Any]:
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(config_path)
        return _load_rules_file(path)

    for candidate in DEFAULT_RULES_CONFIG_PATHS:
        path = Path(candidate)
        if path.exists():
            return _load_rules_file(path)

    return DEFAULT_RULES_CONFIG


def get_privacy_defaults(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or DEFAULT_RULES_CONFIG
    return config.get("privacy_defaults", DEFAULT_RULES_CONFIG["privacy_defaults"])


def get_keep_rules(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or DEFAULT_RULES_CONFIG
    return config.get("keep_rules", DEFAULT_RULES_CONFIG["keep_rules"])


def get_merge_preferences(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or DEFAULT_RULES_CONFIG
    return config.get(
        "playlist_merge_preferences",
        DEFAULT_RULES_CONFIG["playlist_merge_preferences"],
    )


def get_liked_video_review_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or DEFAULT_RULES_CONFIG
    return config.get("liked_video_review", DEFAULT_RULES_CONFIG["liked_video_review"])


def get_category_suggestion_filters(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or DEFAULT_RULES_CONFIG
    return config.get(
        "category_suggestion_filters",
        DEFAULT_RULES_CONFIG["category_suggestion_filters"],
    )


def _load_rules_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        return json.loads(text)
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "PyYAML is required to load YAML rules files. Install dependencies again."
            ) from exc
        return yaml.safe_load(text)
    raise ValueError(f"Unsupported rules config format: {path}")


def build_alias_maps(config: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    playlist_aliases = {
        normalize_key(source): normalize_key(target)
        for source, target in config.get("playlist_aliases", {}).items()
    }
    token_aliases = {
        normalize_key(source): normalize_key(target)
        for source, target in config.get("token_aliases", {}).items()
    }
    return playlist_aliases, token_aliases


def normalize_playlist_title(title: str, config: dict[str, Any] | None = None) -> str:
    normalized = normalize_key(title)
    if not normalized:
        return normalized

    config = config or DEFAULT_RULES_CONFIG
    playlist_aliases, token_aliases = build_alias_maps(config)
    if normalized in playlist_aliases:
        return playlist_aliases[normalized]

    tokens = []
    for token in normalized.split():
        canonical_token = token_aliases.get(token, token)
        tokens.append(singularize_token(canonical_token))

    normalized = normalize_space(" ".join(tokens))
    return playlist_aliases.get(normalized, normalized)


def build_lookup(
    playlists_data: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    exact_lookup = {playlist["title"]: playlist for playlist in playlists_data}
    normalized_lookup: dict[str, list[dict[str, Any]]] = {}

    for playlist in playlists_data:
        key = normalize_playlist_title(playlist["title"], config)
        normalized_lookup.setdefault(key, []).append(playlist)

    return exact_lookup, normalized_lookup


def build_target_video_ids(target: dict[str, Any] | None) -> set[str]:
    if not target:
        return set()

    return {
        item["video_id"]
        for item in target.get("items", [])
        if item.get("video_id")
    }


def match_keyword_sets(title: str, rule: dict[str, Any]) -> list[list[str]]:
    lowered = title.lower()
    matches = []
    for keyword_set in rule.get("keyword_sets", []):
        if all(keyword in lowered for keyword in keyword_set):
            matches.append(keyword_set)
    return matches


def match_weighted_negative_keyword_sets(title: str, rule: dict[str, Any]) -> list[dict[str, Any]]:
    lowered = title.lower()
    matches = []
    for negative_rule in rule.get("negative_keyword_sets", []):
        if isinstance(negative_rule, dict):
            keyword_set = negative_rule.get("keywords", [])
            weight = int(negative_rule.get("weight", 25))
            reason = negative_rule.get("reason", "negative keyword match")
        else:
            keyword_set = negative_rule
            weight = 25
            reason = "negative keyword match"

        if keyword_set and all(keyword.lower() in lowered for keyword in keyword_set):
            matches.append(
                {
                    "keywords": keyword_set,
                    "weight": weight,
                    "reason": reason,
                }
            )
    return matches


def playlist_is_allowed_by_filters(
    title: str,
    allowlist: list[str],
    blocklist: list[str],
) -> bool:
    normalized_title = normalize_key(title)
    normalized_allowlist = {normalize_key(value) for value in allowlist if value.strip()}
    normalized_blocklist = {normalize_key(value) for value in blocklist if value.strip()}
    if normalized_title in normalized_blocklist:
        return False
    return not normalized_allowlist or normalized_title in normalized_allowlist


def validate_rules_config(config: dict[str, Any]) -> list[str]:
    errors = []
    if not isinstance(config, dict):
        return ["Rules config must be a JSON or YAML object."]

    privacy = get_privacy_defaults(config).get("created_playlist_privacy", "private")
    if privacy not in {"private", "unlisted", "public"}:
        errors.append("privacy_defaults.created_playlist_privacy must be private, unlisted, or public.")

    merge_strategy = get_merge_preferences(config).get("canonical_playlist_strategy", "largest_first")
    if merge_strategy not in {"largest_first"}:
        errors.append("playlist_merge_preferences.canonical_playlist_strategy must be largest_first.")

    keep_rules = get_keep_rules(config)
    if not isinstance(keep_rules.get("preferred_playlist_titles", []), list):
        errors.append("keep_rules.preferred_playlist_titles must be a list.")
    privacy_order = keep_rules.get("preferred_privacy_order", [])
    if not isinstance(privacy_order, list):
        errors.append("keep_rules.preferred_privacy_order must be a list.")
    else:
        invalid_privacy = [value for value in privacy_order if value not in {"private", "unlisted", "public"}]
        if invalid_privacy:
            errors.append("keep_rules.preferred_privacy_order contains invalid privacy values.")

    for section_name in ["playlist_aliases", "token_aliases"]:
        if not isinstance(config.get(section_name, {}), dict):
            errors.append(f"{section_name} must be an object.")

    category_filters = get_category_suggestion_filters(config)
    for field in [
        "source_playlist_allowlist",
        "source_playlist_blocklist",
        "target_playlist_allowlist",
        "target_playlist_blocklist",
    ]:
        if not isinstance(category_filters.get(field, []), list) or not all(
            isinstance(value, str) for value in category_filters.get(field, [])
        ):
            errors.append(f"category_suggestion_filters.{field} must be a list of strings.")

    for index, rule in enumerate(config.get("category_rules", []), 1):
        prefix = f"category_rules[{index}]"
        if not isinstance(rule.get("source_playlists", []), list) or not rule.get("source_playlists"):
            errors.append(f"{prefix}.source_playlists must be a non empty list.")
        if not isinstance(rule.get("target_playlist", ""), str) or not rule.get("target_playlist", "").strip():
            errors.append(f"{prefix}.target_playlist must be a non empty string.")
        if not isinstance(rule.get("keyword_sets", []), list) or not rule.get("keyword_sets"):
            errors.append(f"{prefix}.keyword_sets must be a non empty list.")
        for set_index, keyword_set in enumerate(rule.get("keyword_sets", []), 1):
            if not isinstance(keyword_set, list) or not all(isinstance(keyword, str) for keyword in keyword_set):
                errors.append(f"{prefix}.keyword_sets[{set_index}] must be a list of strings.")
        for set_index, negative_rule in enumerate(rule.get("negative_keyword_sets", []), 1):
            if isinstance(negative_rule, dict):
                keyword_set = negative_rule.get("keywords", [])
                weight = negative_rule.get("weight", 25)
            else:
                keyword_set = negative_rule
                weight = 25
            if not isinstance(keyword_set, list) or not all(isinstance(keyword, str) for keyword in keyword_set):
                errors.append(f"{prefix}.negative_keyword_sets[{set_index}] keywords must be a list of strings.")
            if not isinstance(weight, int) or weight < 1 or weight > 100:
                errors.append(f"{prefix}.negative_keyword_sets[{set_index}] weight must be an integer from 1 to 100.")

    return errors


def score_liked_video_flag(
    matched_keyword_sets: list[list[str]],
    severity: str,
) -> tuple[int, str]:
    base = {"low": 55, "medium": 70, "high": 85}.get(severity, 60)
    longest_match = max((len(keyword_set) for keyword_set in matched_keyword_sets), default=1)
    score = min(100, base + max(0, longest_match - 1) * 5)
    label = "high" if score >= 80 else "medium" if score >= 65 else "low"
    return score, label


def find_liked_video_flags(
    playlists_data: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = config or DEFAULT_RULES_CONFIG
    review_config = get_liked_video_review_config(config)
    if not review_config.get("enabled", True):
        return []

    liked_titles = {
        title.strip().lower()
        for title in review_config.get("liked_playlist_titles", [])
        if title.strip()
    }
    if not liked_titles:
        liked_titles = {"liked videos"}

    flags = []
    for playlist in playlists_data:
        if playlist["title"].strip().lower() not in liked_titles:
            continue

        for item in playlist.get("items", []):
            for rule in review_config.get("self_image_flag_rules", []):
                matched_keyword_sets = match_keyword_sets(item.get("title", ""), rule)
                if not matched_keyword_sets:
                    continue

                severity = rule.get("severity", "medium")
                confidence_score, confidence_label = score_liked_video_flag(matched_keyword_sets, severity)
                flattened_keywords = sorted(
                    {keyword for keyword_set in matched_keyword_sets for keyword in keyword_set}
                )

                flags.append(
                    {
                        "playlist_title": playlist["title"],
                        "video_id": item.get("video_id", ""),
                        "title": item.get("title", ""),
                        "playlist_item_id": item.get("id", ""),
                        "position": item.get("position", 0),
                        "reason": rule.get("reason", "Review this liked video."),
                        "severity": severity,
                        "matched_keyword_sets": matched_keyword_sets,
                        "matched_keywords": flattened_keywords,
                        "confidence_score": confidence_score,
                        "confidence_label": confidence_label,
                    }
                )
                break

    flags.sort(
        key=lambda item: (
            -item["confidence_score"],
            item["playlist_title"].lower(),
            item["title"].lower(),
            item["video_id"],
        )
    )
    return flags


def score_move_confidence(
    title: str,
    source_title: str,
    target_title: str,
    matched_keyword_sets: list[list[str]],
    negative_matches: list[dict[str, Any]],
    target_exists: bool,
) -> tuple[int, str, list[str]]:
    score = 45
    reasons = []

    if matched_keyword_sets:
        longest_match = max(len(keyword_set) for keyword_set in matched_keyword_sets)
        keyword_score = min(25, 10 + (longest_match - 1) * 5)
        score += keyword_score
        flattened_keywords = sorted({keyword for keyword_set in matched_keyword_sets for keyword in keyword_set})
        reasons.append(f"matched keywords: {', '.join(flattened_keywords)}")

    for negative_match in negative_matches:
        score -= negative_match["weight"]
        reasons.append(
            f"negative keywords: {', '.join(negative_match['keywords'])} "
            f"(-{negative_match['weight']}, {negative_match['reason']})"
        )

    if target_exists:
        score += 10
        reasons.append("target playlist already exists")
    else:
        reasons.append("target playlist would need to be created")

    if normalize_key(target_title) in normalize_key(title):
        score += 10
        reasons.append("target playlist title appears directly in the video title")

    generic_sources = {"ai", "tech", "diy", "favorites", "training", "workout", "health"}
    if normalize_key(source_title) in generic_sources:
        score += 5
        reasons.append("source playlist is broad, so a move is more likely to help")

    score = max(0, min(score, 100))
    if score >= 80:
        label = "high"
    elif score >= 60:
        label = "medium"
    else:
        label = "low"

    reasons.append(f"base rule: {source_title} -> {target_title}")
    return score, label, reasons


def find_category_moves(
    playlists_data: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = config or DEFAULT_RULES_CONFIG
    playlist_lookup, normalized_lookup = build_lookup(playlists_data, config)
    category_filters = get_category_suggestion_filters(config)
    moves = []

    for rule in config.get("category_rules", []):
        source_playlists = rule.get("source_playlists", [])
        if not playlist_is_allowed_by_filters(
            rule["target_playlist"],
            category_filters.get("target_playlist_allowlist", []),
            category_filters.get("target_playlist_blocklist", []),
        ):
            continue
        target_candidates = normalized_lookup.get(
            normalize_playlist_title(rule["target_playlist"], config),
            [],
        )
        target = target_candidates[0] if target_candidates else playlist_lookup.get(rule["target_playlist"])
        target_video_ids = build_target_video_ids(target)

        for source_title in source_playlists:
            if not playlist_is_allowed_by_filters(
                source_title,
                category_filters.get("source_playlist_allowlist", []),
                category_filters.get("source_playlist_blocklist", []),
            ):
                continue
            source = playlist_lookup.get(source_title)
            if not source:
                continue

            for item in source.get("items", []):
                matched_keyword_sets = match_keyword_sets(item.get("title", ""), rule)
                if not matched_keyword_sets:
                    continue
                negative_matches = match_weighted_negative_keyword_sets(item.get("title", ""), rule)
                if item["video_id"] in target_video_ids:
                    continue

                confidence_score, confidence_label, confidence_reasons = score_move_confidence(
                    title=item["title"],
                    source_title=source["title"],
                    target_title=rule["target_playlist"],
                    matched_keyword_sets=matched_keyword_sets,
                    negative_matches=negative_matches,
                    target_exists=target is not None,
                )
                if confidence_score < int(rule.get("minimum_confidence", 50)):
                    continue

                moves.append(
                    {
                        "action": "move_to_playlist",
                        "video_id": item["video_id"],
                        "title": item["title"],
                        "from_playlist": {
                            "playlist_id": source["id"],
                            "playlist_title": source["title"],
                            "playlist_privacy": source.get("privacy", ""),
                            "playlist_item_id": item["id"],
                            "position": item.get("position", 0),
                        },
                        "to_playlist": {
                            "playlist_id": (target or {}).get("id"),
                            "playlist_title": (target or {}).get("title", rule["target_playlist"]),
                            "playlist_privacy": (target or {}).get("privacy", source.get("privacy", "private")),
                        },
                        "rule": rule["reason"],
                        "matched_keyword_sets": matched_keyword_sets,
                        "negative_keyword_matches": negative_matches,
                        "confidence_score": confidence_score,
                        "confidence_label": confidence_label,
                        "confidence_reasons": confidence_reasons,
                    }
                )

    moves.sort(
        key=lambda move: (
            -move["confidence_score"],
            move["from_playlist"]["playlist_title"].lower(),
            move["to_playlist"]["playlist_title"].lower(),
            move["title"].lower(),
            move["video_id"],
        )
    )
    return moves


def find_same_title_playlist_merges(
    playlists_data: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    config = config or DEFAULT_RULES_CONFIG
    merge_preferences = get_merge_preferences(config)
    prefer_private_target = merge_preferences.get("prefer_private_target", True)

    for playlist in playlists_data:
        grouped.setdefault(normalize_playlist_title(playlist["title"], config), []).append(playlist)

    merges = []
    for normalized_title, group in grouped.items():
        if len(group) < 2:
            continue

        ordered = sorted(
            group,
            key=lambda playlist: (
                -len(playlist.get("items", [])),
                playlist.get("privacy", "") != "private" if prefer_private_target else False,
                playlist["id"],
            ),
        )
        target = ordered[0]
        target_video_ids = {
            item["video_id"]
            for item in target.get("items", [])
            if item.get("video_id")
        }

        for source in ordered[1:]:
            move_items = []
            remove_items = []

            for item in source.get("items", []):
                payload = {
                    "playlist_item_id": item["id"],
                    "video_id": item["video_id"],
                    "title": item["title"],
                    "position": item.get("position", 0),
                }
                if item["video_id"] in target_video_ids:
                    remove_items.append(payload)
                    continue

                move_items.append(payload)
                target_video_ids.add(item["video_id"])

            merges.append(
                {
                    "action": "merge_playlist",
                    "reason": "Duplicate or aliased playlist title",
                    "normalized_title": normalized_title,
                    "source_playlist": {
                        "playlist_id": source["id"],
                        "playlist_title": source["title"],
                        "playlist_privacy": source.get("privacy", ""),
                        "item_count": len(source.get("items", [])),
                    },
                    "target_playlist": {
                        "playlist_id": target["id"],
                        "playlist_title": target["title"],
                        "playlist_privacy": target.get("privacy", ""),
                        "item_count": len(target.get("items", [])),
                    },
                    "move_items": move_items,
                    "remove_items": remove_items,
                }
            )

    merges.sort(
        key=lambda merge: (
            merge["normalized_title"],
            merge["source_playlist"]["playlist_id"],
        )
    )
    return merges


def build_overlap_review(
    playlists_data: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = config or DEFAULT_RULES_CONFIG
    reviews = []
    for index, left in enumerate(playlists_data):
        left_videos = {
            item["video_id"]
            for item in left.get("items", [])
            if item.get("video_id")
        }
        if not left_videos:
            continue

        for right in playlists_data[index + 1:]:
            right_videos = {
                item["video_id"]
                for item in right.get("items", [])
                if item.get("video_id")
            }
            if not right_videos:
                continue

            shared = len(left_videos & right_videos)
            if shared == 0:
                continue

            union = len(left_videos | right_videos)
            jaccard = shared / union
            containment = max(shared / len(left_videos), shared / len(right_videos))

            left_normalized = normalize_playlist_title(left["title"], config)
            right_normalized = normalize_playlist_title(right["title"], config)
            aliased_match = left_normalized == right_normalized
            if not aliased_match and shared < 3 and jaccard < 0.10 and containment < 0.35:
                continue

            reasons = []
            if aliased_match:
                reasons.append(f"normalized titles match as `{left_normalized}`")
            if shared >= 3:
                reasons.append(f"{shared} shared videos")
            if containment >= 0.35:
                reasons.append(f"high containment {containment:.3f}")
            if jaccard >= 0.10:
                reasons.append(f"meaningful overlap {jaccard:.3f}")

            reviews.append(
                {
                    "left_playlist": left["title"],
                    "right_playlist": right["title"],
                    "left_normalized": left_normalized,
                    "right_normalized": right_normalized,
                    "shared_videos": shared,
                    "left_count": len(left_videos),
                    "right_count": len(right_videos),
                    "jaccard": round(jaccard, 3),
                    "containment": round(containment, 3),
                    "merge_candidate": aliased_match,
                    "review_reason": "; ".join(reasons) if reasons else "overlap threshold met",
                }
            )

    reviews.sort(
        key=lambda review: (
            not review["merge_candidate"],
            -review["shared_videos"],
            -review["jaccard"],
            review["left_playlist"].lower(),
            review["right_playlist"].lower(),
        )
    )
    return reviews
