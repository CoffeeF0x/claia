"""
The ExoFox family look as Textual themes.

Tokens come from the platform design system (docs repo,
``design/colors.md``): warm stone surfaces, kintsugi gold for
focus/accents/borders that matter (never large fills), warm
semantic colors. Dark is the default; light is a runtime-switchable
counterpart built from the same palette's light end.

Custom variables carried for widget CSS:

- ``$user-label`` — the YOU micro-label (info teal, distinct from
  the gold agent labels).
"""

# External dependencies
from textual.theme import Theme



########################################################################
#                               THEMES                                 #
########################################################################
EXOFOX_DARK = Theme(
  name="exofox",
  primary="#C49A3A",      # gold-500 — the kintsugi line
  secondary="#E2C47E",    # gold-300
  accent="#C49A3A",
  foreground="#F0EBE3",   # text-primary
  background="#1A1816",   # surface-900
  surface="#211F1C",      # surface-850
  panel="#2A2724",        # surface-800
  success="#5B8C5A",
  warning="#D4883A",
  error="#C45B4A",
  dark=True,
  variables={
    "border": "#C49A3A",             # focus ring gold
    "border-blurred": "#3A3633",     # surface-700 resting borders
    "text-muted": "#A39E95",         # text-secondary
    "link-color": "#E2C47E",
    "input-selection-background": "#C49A3A 35%",
    "user-label": "#4A8B8C",         # info teal
    # Scrollbars: invisible track, stone thumb, gold under the hand.
    "scrollbar": "#3A3633",
    "scrollbar-hover": "#6B5A2E",
    "scrollbar-active": "#C49A3A",
    "scrollbar-background": "#1A1816",
    "scrollbar-background-hover": "#1A1816",
    "scrollbar-background-active": "#1A1816",
    "scrollbar-corner-color": "#1A1816",
  },
)


EXOFOX_LIGHT = Theme(
  name="exofox-light",
  primary="#A67E2C",      # gold-600 — contrast on light stone
  secondary="#856320",    # gold-700
  accent="#A67E2C",
  foreground="#1A1816",   # text-primary (light)
  background="#F8F6F3",   # surface-50
  surface="#EFECE8",      # surface-100
  panel="#E5E1DC",        # surface-150
  success="#5B8C5A",
  warning="#D4883A",
  error="#C45B4A",
  dark=False,
  variables={
    "border": "#A67E2C",
    "border-blurred": "#D5D1CC",     # surface-200
    "text-muted": "#5E5955",         # text-secondary (light)
    "link-color": "#856320",
    "input-selection-background": "#D4A94C 35%",
    "user-label": "#4A8B8C",
    # Scrollbars: invisible track, stone thumb, gold under the hand.
    "scrollbar": "#D5D1CC",
    "scrollbar-hover": "#C4AE6E",
    "scrollbar-active": "#A67E2C",
    "scrollbar-background": "#F8F6F3",
    "scrollbar-background-hover": "#F8F6F3",
    "scrollbar-background-active": "#F8F6F3",
    "scrollbar-corner-color": "#F8F6F3",
  },
)
