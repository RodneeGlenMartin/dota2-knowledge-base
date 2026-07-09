"""Build the itemization app dataset.

Combines the Valve-sourced hero/item KB (data/heroes, data/items) with a
curated itemization layer (positions, core builds, threat tags, counter
rules) and emits:

  - data/app/itemization.json   (canonical dataset)
  - app/data.js                 (same data as a JS global for file:// use)

Every item slug referenced here is validated against data/items/_index.json;
unknown slugs abort the build.

Usage: python scripts/build_itemization.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEROES_DIR = ROOT / "data" / "heroes"
ITEMS_DIR = ROOT / "data" / "items"
OUT_JSON = ROOT / "data" / "app" / "itemization.json"
OUT_JS = ROOT / "app" / "data.js"

# ---------------------------------------------------------------------------
# Positions: curated per-hero viable positions (1=safelane carry, 2=mid,
# 3=offlane, 4=soft support, 5=hard support). First entry = most common.
# ---------------------------------------------------------------------------
POSITIONS: dict[str, list[int]] = {
    "abaddon": [3, 4, 5],
    "alchemist": [1, 2],
    "ancient_apparition": [5, 4],
    "anti_mage": [1],
    "arc_warden": [1, 2],
    "axe": [3],
    "bane": [5, 4],
    "batrider": [3, 4, 2],
    "beastmaster": [3, 4],
    "bloodseeker": [1, 3, 2],
    "bounty_hunter": [4],
    "brewmaster": [3, 4],
    "bristleback": [3, 1],
    "broodmother": [3, 2],
    "centaur_warrunner": [3],
    "chaos_knight": [1, 3],
    "chen": [5, 4],
    "clinkz": [1, 2, 3],
    "clockwerk": [4, 3],
    "crystal_maiden": [5],
    "dark_seer": [3],
    "dark_willow": [4, 5],
    "dawnbreaker": [3, 4],
    "dazzle": [5, 4],
    "death_prophet": [2, 3],
    "disruptor": [5, 4],
    "doom": [3],
    "dragon_knight": [2, 3, 1],
    "drow_ranger": [1, 2],
    "earth_spirit": [4, 5],
    "earthshaker": [4, 5, 3],
    "elder_titan": [4, 5],
    "ember_spirit": [2, 1],
    "enchantress": [5, 4, 3],
    "enigma": [3, 4],
    "faceless_void": [1],
    "grimstroke": [5, 4],
    "gyrocopter": [1, 4],
    "hoodwink": [4, 5],
    "huskar": [2, 1, 3],
    "invoker": [2, 4],
    "io": [5, 4],
    "jakiro": [5, 4],
    "juggernaut": [1],
    "keeper_of_the_light": [5, 4],
    "kez": [1, 2],
    "kunkka": [2, 3, 4],
    "largo": [4, 5],
    "legion_commander": [3, 4],
    "leshrac": [2, 3, 5],
    "lich": [5, 4],
    "lifestealer": [1, 3],
    "lina": [2, 5, 4],
    "lion": [5, 4],
    "lone_druid": [1, 2],
    "luna": [1, 2],
    "lycan": [1, 3],
    "magnus": [3, 4, 2],
    "marci": [4, 1, 3],
    "mars": [3, 2],
    "medusa": [1, 2],
    "meepo": [2, 1],
    "mirana": [4, 2, 1],
    "monkey_king": [1, 2, 4],
    "morphling": [1, 2],
    "muerta": [1, 2],
    "naga_siren": [1, 5],
    "nature_s_prophet": [3, 4, 1, 2],
    "necrophos": [2, 3],
    "night_stalker": [3, 4],
    "nyx_assassin": [4, 3],
    "ogre_magi": [4, 5],
    "omniknight": [5, 4, 3],
    "oracle": [5, 4],
    "outworld_destroyer": [2, 3],
    "pangolier": [3, 2, 4],
    "phantom_assassin": [1],
    "phantom_lancer": [1],
    "phoenix": [4, 5, 3],
    "primal_beast": [3, 4],
    "puck": [2, 3, 4],
    "pudge": [4, 2, 3],
    "pugna": [2, 5, 4],
    "queen_of_pain": [2],
    "razor": [2, 3, 1],
    "riki": [4, 1],
    "ringmaster": [5, 4],
    "rubick": [4, 5],
    "sand_king": [3, 4],
    "shadow_demon": [5, 4],
    "shadow_fiend": [2],
    "shadow_shaman": [5, 4],
    "silencer": [5, 4, 2],
    "skywrath_mage": [4, 5],
    "slardar": [3, 4],
    "slark": [1],
    "snapfire": [4, 5],
    "sniper": [2, 1, 4],
    "spectre": [1],
    "spirit_breaker": [4, 3],
    "storm_spirit": [2],
    "sven": [1, 3],
    "techies": [4, 5, 3],
    "templar_assassin": [2, 1],
    "terrorblade": [1],
    "tidehunter": [3, 5],
    "timbersaw": [3, 2],
    "tinker": [2],
    "tiny": [2, 3, 4],
    "treant_protector": [5, 4],
    "troll_warlord": [1],
    "tusk": [4, 3],
    "underlord": [3],
    "undying": [4, 5, 3],
    "ursa": [1, 4],
    "vengeful_spirit": [5, 4],
    "venomancer": [4, 5, 3],
    "viper": [2, 3, 1],
    "visage": [4, 2],
    "void_spirit": [2, 3, 4],
    "warlock": [5, 4],
    "weaver": [1, 4, 3],
    "windranger": [4, 2, 1],
    "winter_wyvern": [5, 4],
    "witch_doctor": [5, 4],
    "wraith_king": [1, 3],
    "zeus": [2, 4, 5],
}

# ---------------------------------------------------------------------------
# Curated core builds: hero slug -> {position: [item slugs in build order]}.
# "*" applies to every listed position without a specific entry.
# ---------------------------------------------------------------------------
CORE_BUILDS: dict[str, dict[str, list[str]]] = {
    "abaddon": {"3": ["vanguard", "blade_mail", "crimson_guard", "shiva_s_guard"],
                 "*": ["solar_crest", "holy_locket", "glimmer_cape", "vladmir_s_offering"]},
    "alchemist": {"*": ["power_treads", "radiance", "black_king_bar", "assault_cuirass", "abyssal_blade", "moon_shard"]},
    "ancient_apparition": {"*": ["glimmer_cape", "aghanim_s_scepter", "aether_lens", "force_staff"]},
    "anti_mage": {"1": ["power_treads", "battle_fury", "manta_style", "skull_basher", "butterfly", "abyssal_blade"]},
    "arc_warden": {"*": ["hand_of_midas", "maelstrom", "manta_style", "mjollnir", "silver_edge", "bloodthorn"]},
    "axe": {"3": ["vanguard", "blink_dagger", "blade_mail", "crimson_guard", "aghanim_s_shard", "heart_of_tarrasque"]},
    "bane": {"*": ["glimmer_cape", "aether_lens", "force_staff", "aeon_disk"]},
    "batrider": {"3": ["boots_of_travel", "blink_dagger", "black_king_bar", "aghanim_s_shard", "octarine_core"],
                  "*": ["blink_dagger", "force_staff", "aghanim_s_shard", "black_king_bar"]},
    "beastmaster": {"*": ["helm_of_the_dominator", "boots_of_bearing", "aghanim_s_scepter", "helm_of_the_overlord", "refresher_orb"]},
    "bloodseeker": {"*": ["phase_boots", "maelstrom", "black_king_bar", "sange_and_yasha", "satanic", "abyssal_blade"]},
    "bounty_hunter": {"4": ["orb_of_corrosion", "phase_boots", "solar_crest", "aghanim_s_scepter", "octarine_core"]},
    "brewmaster": {"*": ["boots_of_bearing", "blink_dagger", "radiance", "aghanim_s_scepter", "refresher_orb"]},
    "bristleback": {"*": ["vanguard", "arcane_boots", "soul_ring", "bloodstone", "eternal_shroud", "heart_of_tarrasque"]},
    "broodmother": {"*": ["soul_ring", "orchid_malevolence", "black_king_bar", "bloodthorn", "butterfly", "abyssal_blade"]},
    "centaur_warrunner": {"3": ["vanguard", "blink_dagger", "crimson_guard", "heart_of_tarrasque", "overwhelming_blink", "aghanim_s_scepter"]},
    "chaos_knight": {"*": ["power_treads", "armlet_of_mordiggian", "echo_sabre", "black_king_bar", "heart_of_tarrasque", "abyssal_blade"]},
    "chen": {"*": ["holy_locket", "mekansm", "guardian_greaves", "solar_crest", "aghanim_s_scepter"]},
    "clinkz": {"*": ["power_treads", "maelstrom", "orchid_malevolence", "dragon_lance", "bloodthorn", "greater_crit"],
                "_fix": []},
    "clockwerk": {"*": ["tranquil_boots", "force_staff", "blade_mail", "aghanim_s_scepter", "shiva_s_guard"]},
    "crystal_maiden": {"5": ["tranquil_boots", "glimmer_cape", "force_staff", "aghanim_s_shard", "black_king_bar", "aghanim_s_scepter"]},
    "dark_seer": {"3": ["arcane_boots", "blink_dagger", "guardian_greaves", "pipe_of_insight", "shiva_s_guard", "octarine_core"]},
    "dark_willow": {"*": ["null_talisman", "aether_lens", "blink_dagger", "aghanim_s_scepter", "octarine_core", "moon_shard"]},
    "dawnbreaker": {"3": ["phase_boots", "echo_sabre", "desolator", "black_king_bar", "assault_cuirass"],
                     "*": ["arcane_boots", "holy_locket", "guardian_greaves", "aghanim_s_scepter"]},
    "dazzle": {"*": ["arcane_boots", "glimmer_cape", "aghanim_s_shard", "guardian_greaves", "aghanim_s_scepter"]},
    "death_prophet": {"*": ["null_talisman", "phase_boots", "eul_s_scepter_of_divinity", "black_king_bar", "octarine_core", "shiva_s_guard"]},
    "disruptor": {"*": ["glimmer_cape", "aghanim_s_scepter", "aether_lens", "force_staff", "refresher_orb"]},
    "doom": {"3": ["phase_boots", "hand_of_midas", "blink_dagger", "black_king_bar", "shiva_s_guard", "refresher_orb"]},
    "dragon_knight": {"*": ["power_treads", "hand_of_midas", "blink_dagger", "black_king_bar", "aghanim_s_scepter", "assault_cuirass"]},
    "drow_ranger": {"*": ["power_treads", "dragon_lance", "manta_style", "hurricane_pike", "silver_edge", "butterfly"]},
    "earth_spirit": {"*": ["urn_of_shadows", "tranquil_boots", "spirit_vessel", "aghanim_s_scepter", "black_king_bar", "octarine_core"]},
    "earthshaker": {"*": ["arcane_boots", "blink_dagger", "aghanim_s_scepter", "aghanim_s_shard", "octarine_core", "refresher_orb"]},
    "elder_titan": {"*": ["tranquil_boots", "solar_crest", "force_staff", "aghanim_s_scepter", "greater_crit"],
                     "_fix": []},
    "ember_spirit": {"*": ["phase_boots", "maelstrom", "black_king_bar", "gleipnir", "octarine_core", "radiance"]},
    "enchantress": {"*": ["power_treads", "holy_locket", "solar_crest", "aghanim_s_scepter", "hurricane_pike"]},
    "enigma": {"*": ["arcane_boots", "blink_dagger", "black_king_bar", "refresher_orb", "aghanim_s_scepter", "shiva_s_guard"]},
    "faceless_void": {"1": ["power_treads", "mask_of_madness", "maelstrom", "black_king_bar", "mjollnir", "butterfly"]},
    "grimstroke": {"*": ["aether_lens", "glimmer_cape", "aghanim_s_shard", "aghanim_s_scepter", "octarine_core"]},
    "gyrocopter": {"1": ["power_treads", "lesser_crit", "black_king_bar", "satanic", "butterfly", "greater_crit"],
                    "4": ["urn_of_shadows", "arcane_boots", "veil_of_discord", "aghanim_s_scepter", "force_staff"],
                    "_fix": []},
    "hoodwink": {"*": ["arcane_boots", "aether_lens", "gleipnir", "aghanim_s_scepter", "octarine_core"]},
    "huskar": {"*": ["armlet_of_mordiggian", "power_treads", "black_king_bar", "heaven_s_halberd", "satanic", "assault_cuirass"]},
    "invoker": {"2": ["hand_of_midas", "boots_of_travel", "aghanim_s_scepter", "black_king_bar", "refresher_orb", "octarine_core"],
                 "*": ["urn_of_shadows", "spirit_vessel", "aether_lens", "aghanim_s_scepter", "blink_dagger"]},
    "io": {"*": ["magic_wand", "holy_locket", "mekansm", "glimmer_cape", "aghanim_s_scepter", "heart_of_tarrasque"]},
    "jakiro": {"*": ["arcane_boots", "glimmer_cape", "aether_lens", "aghanim_s_scepter", "refresher_orb"]},
    "juggernaut": {"1": ["phase_boots", "battle_fury", "manta_style", "aghanim_s_shard", "butterfly", "abyssal_blade"]},
    "keeper_of_the_light": {"*": ["tranquil_boots", "glimmer_cape", "force_staff", "aghanim_s_shard", "aghanim_s_scepter"]},
    "kez": {"*": ["power_treads", "echo_sabre", "black_king_bar", "basher_alt", "butterfly", "abyssal_blade"],
             "_fix": []},
    "kunkka": {"*": ["phase_boots", "armlet_of_mordiggian", "black_king_bar", "assault_cuirass", "greater_crit", "overwhelming_blink"],
                "_fix": []},
    "largo": {"*": ["arcane_boots", "aether_lens", "glimmer_cape", "force_staff", "aghanim_s_scepter"]},
    "legion_commander": {"3": ["phase_boots", "blade_mail", "blink_dagger", "black_king_bar", "aghanim_s_scepter", "overwhelming_blink"]},
    "leshrac": {"*": ["arcane_boots", "bloodstone", "eul_s_scepter_of_divinity", "black_king_bar", "shiva_s_guard", "octarine_core"]},
    "lich": {"*": ["glimmer_cape", "aether_lens", "force_staff", "aghanim_s_scepter", "octarine_core"]},
    "lifestealer": {"*": ["power_treads", "armlet_of_mordiggian", "desolator", "basher_alt", "abyssal_blade", "satanic"],
                     "_fix": []},
    "lina": {"2": ["null_talisman", "power_treads", "aether_lens", "aghanim_s_scepter", "black_king_bar", "octarine_core"],
              "*": ["null_talisman", "aether_lens", "aghanim_s_shard", "aghanim_s_scepter", "octarine_core"]},
    "lion": {"*": ["tranquil_boots", "blink_dagger", "aether_lens", "aghanim_s_shard", "aghanim_s_scepter", "octarine_core"]},
    "lone_druid": {"*": ["orb_of_corrosion", "phase_boots", "assault_cuirass", "desolator", "black_king_bar", "moon_shard"]},
    "luna": {"1": ["power_treads", "mask_of_madness", "manta_style", "black_king_bar", "butterfly", "satanic"]},
    "lycan": {"*": ["helm_of_the_dominator", "power_treads", "aghanim_s_scepter", "helm_of_the_overlord", "black_king_bar", "assault_cuirass"]},
    "magnus": {"3": ["arcane_boots", "blink_dagger", "black_king_bar", "aghanim_s_scepter", "refresher_orb"],
                "2": ["power_treads", "echo_sabre", "blink_dagger", "black_king_bar", "harpoon"],
                "*": ["arcane_boots", "blink_dagger", "force_staff", "aghanim_s_shard", "refresher_orb"]},
    "marci": {"*": ["phase_boots", "echo_sabre", "black_king_bar", "basher_alt", "harpoon", "abyssal_blade"],
               "_fix": []},
    "mars": {"3": ["phase_boots", "blink_dagger", "black_king_bar", "desolator", "refresher_orb", "overwhelming_blink"]},
    "medusa": {"*": ["power_treads", "manta_style", "dragon_lance", "skadi_alt", "butterfly", "hurricane_pike"],
                "_fix": []},
    "meepo": {"*": ["diffusal_blade", "power_treads", "dragon_lance", "skadi_alt", "aghanim_s_scepter", "heart_of_tarrasque"],
               "_fix": []},
    "mirana": {"*": ["urn_of_shadows", "arcane_boots", "spirit_vessel", "gleipnir", "aghanim_s_scepter", "octarine_core"]},
    "monkey_king": {"1": ["orb_of_corrosion", "power_treads", "echo_sabre", "black_king_bar", "basher_alt", "abyssal_blade"],
                     "*": ["orb_of_corrosion", "power_treads", "diffusal_blade", "black_king_bar", "abyssal_blade"],
                     "_fix": []},
    "morphling": {"*": ["power_treads", "yasha", "manta_style", "black_king_bar", "skadi_alt", "satanic"],
                   "_fix": []},
    "muerta": {"*": ["power_treads", "maelstrom", "hurricane_pike", "black_king_bar", "mjollnir", "greater_crit"],
                "_fix": []},
    "naga_siren": {"1": ["power_treads", "diffusal_blade", "manta_style", "orchid_malevolence", "butterfly", "abyssal_blade"],
                    "5": ["arcane_boots", "aghanim_s_shard", "glimmer_cape", "force_staff", "aghanim_s_scepter"]},
    "nature_s_prophet": {"*": ["power_treads", "hand_of_midas", "orchid_malevolence", "black_king_bar", "silver_edge", "bloodthorn"]},
    "necrophos": {"*": ["null_talisman", "boots_of_travel", "radiance", "aghanim_s_shard", "shiva_s_guard", "octarine_core"]},
    "night_stalker": {"*": ["phase_boots", "echo_sabre", "black_king_bar", "aghanim_s_scepter", "basher_alt", "abyssal_blade"],
                       "_fix": []},
    "nyx_assassin": {"*": ["urn_of_shadows", "arcane_boots", "dagon", "aghanim_s_scepter", "ethereal_blade", "octarine_core"]},
    "ogre_magi": {"*": ["arcane_boots", "aether_lens", "solar_crest", "aghanim_s_scepter", "heart_of_tarrasque"]},
    "omniknight": {"*": ["arcane_boots", "holy_locket", "guardian_greaves", "aghanim_s_shard", "aghanim_s_scepter"]},
    "oracle": {"*": ["glimmer_cape", "aether_lens", "aghanim_s_shard", "aeon_disk", "aghanim_s_scepter"]},
    "outworld_destroyer": {"*": ["power_treads", "hand_of_midas", "witch_blade", "black_king_bar", "hurricane_pike", "scythe_of_vyse"]},
    "pangolier": {"*": ["orb_of_corrosion", "arcane_boots", "blink_dagger", "aghanim_s_scepter", "octarine_core", "linken_s_sphere"]},
    "phantom_assassin": {"1": ["power_treads", "battle_fury", "desolator", "black_king_bar", "basher_alt", "satanic"],
                          "_fix": []},
    "phantom_lancer": {"1": ["power_treads", "diffusal_blade", "manta_style", "heart_of_tarrasque", "skadi_alt", "butterfly"],
                        "_fix": []},
    "phoenix": {"*": ["urn_of_shadows", "tranquil_boots", "spirit_vessel", "aghanim_s_shard", "shiva_s_guard", "refresher_orb"]},
    "primal_beast": {"3": ["vanguard", "phase_boots", "blade_mail", "black_king_bar", "aghanim_s_shard", "shiva_s_guard"]},
    "puck": {"2": ["null_talisman", "witch_blade", "blink_dagger", "aghanim_s_scepter", "octarine_core", "linken_s_sphere"]},
    "pudge": {"*": ["tranquil_boots", "blink_dagger", "aether_lens", "aghanim_s_shard", "aghanim_s_scepter", "octarine_core"]},
    "pugna": {"*": ["null_talisman", "arcane_boots", "aether_lens", "aghanim_s_scepter", "octarine_core", "boots_of_travel"]},
    "queen_of_pain": {"2": ["null_talisman", "power_treads", "orchid_malevolence", "black_king_bar", "scythe_of_vyse", "bloodthorn"]},
    "razor": {"*": ["phase_boots", "sange_and_yasha", "black_king_bar", "eul_s_scepter_of_divinity", "refresher_orb", "satanic"]},
    "riki": {"4": ["orb_of_corrosion", "meteor_hammer", "diffusal_blade", "aghanim_s_scepter", "octarine_core"],
              "1": ["power_treads", "diffusal_blade", "manta_style", "basher_alt", "butterfly", "abyssal_blade"],
              "_fix": []},
    "ringmaster": {"*": ["arcane_boots", "aether_lens", "glimmer_cape", "aghanim_s_scepter", "octarine_core"]},
    "rubick": {"*": ["arcane_boots", "aether_lens", "blink_dagger", "aghanim_s_shard", "aghanim_s_scepter", "octarine_core"]},
    "sand_king": {"*": ["arcane_boots", "blink_dagger", "veil_of_discord", "aghanim_s_shard", "shiva_s_guard", "octarine_core"]},
    "shadow_demon": {"*": ["glimmer_cape", "aether_lens", "aghanim_s_shard", "aghanim_s_scepter", "refresher_orb"]},
    "shadow_fiend": {"2": ["power_treads", "mask_of_madness", "dragon_lance", "black_king_bar", "hurricane_pike", "satanic"]},
    "shadow_shaman": {"*": ["arcane_boots", "aether_lens", "blink_dagger", "aghanim_s_scepter", "refresher_orb"]},
    "silencer": {"*": ["null_talisman", "glimmer_cape", "force_staff", "aghanim_s_scepter", "hurricane_pike", "scythe_of_vyse"]},
    "skywrath_mage": {"*": ["null_talisman", "rod_of_atos", "aghanim_s_shard", "aether_lens", "ethereal_blade", "octarine_core"]},
    "slardar": {"3": ["power_treads", "blink_dagger", "black_king_bar", "aghanim_s_shard", "assault_cuirass", "abyssal_blade"]},
    "slark": {"1": ["power_treads", "echo_sabre", "silver_edge", "black_king_bar", "skadi_alt", "abyssal_blade"],
               "_fix": []},
    "snapfire": {"*": ["arcane_boots", "aether_lens", "glimmer_cape", "aghanim_s_scepter", "octarine_core"]},
    "sniper": {"2": ["power_treads", "dragon_lance", "maelstrom", "hurricane_pike", "mjollnir", "greater_crit"],
                "4": ["urn_of_shadows", "arcane_boots", "aghanim_s_shard", "aghanim_s_scepter", "force_staff"],
                "_fix": []},
    "spectre": {"1": ["power_treads", "radiance", "manta_style", "diffusal_blade", "heart_of_tarrasque", "butterfly"]},
    "spirit_breaker": {"*": ["urn_of_shadows", "phase_boots", "wind_lace", "black_king_bar", "silver_edge", "abyssal_blade"]},
    "storm_spirit": {"2": ["power_treads", "witch_blade", "kaya_and_sange", "black_king_bar", "bloodstone", "scythe_of_vyse"]},
    "sven": {"1": ["power_treads", "mask_of_madness", "echo_sabre", "black_king_bar", "harpoon", "greater_crit"],
              "_fix": []},
    "techies": {"*": ["arcane_boots", "aether_lens", "glimmer_cape", "octarine_core", "aghanim_s_scepter", "scythe_of_vyse"]},
    "templar_assassin": {"*": ["power_treads", "desolator", "blink_dagger", "black_king_bar", "nullifier", "swift_blink"]},
    "terrorblade": {"1": ["power_treads", "manta_style", "dragon_lance", "skadi_alt", "satanic", "butterfly"],
                     "_fix": []},
    "tidehunter": {"3": ["arcane_boots", "blink_dagger", "shiva_s_guard", "refresher_orb", "aghanim_s_shard"],
                    "5": ["arcane_boots", "blink_dagger", "pipe_of_insight", "guardian_greaves", "refresher_orb"]},
    "timbersaw": {"*": ["soul_ring", "arcane_boots", "kaya_and_sange", "eternal_shroud", "aghanim_s_scepter", "shiva_s_guard"]},
    "tinker": {"2": ["bottle", "soul_ring", "blink_dagger", "aether_lens", "shiva_s_guard", "ethereal_blade"]},
    "tiny": {"2": ["bottle", "blink_dagger", "echo_sabre", "black_king_bar", "aghanim_s_scepter", "assault_cuirass"],
              "*": ["arcane_boots", "blink_dagger", "force_staff", "aghanim_s_shard", "shiva_s_guard"]},
    "treant_protector": {"*": ["arcane_boots", "blink_dagger", "meteor_hammer", "aghanim_s_shard", "aghanim_s_scepter", "refresher_orb"]},
    "troll_warlord": {"1": ["power_treads", "battle_fury", "sange_and_yasha", "black_king_bar", "basher_alt", "satanic"],
                       "_fix": []},
    "tusk": {"*": ["phase_boots", "solar_crest", "blink_dagger", "aghanim_s_shard", "aghanim_s_scepter", "silver_edge"]},
    "underlord": {"3": ["arcane_boots", "vanguard", "pipe_of_insight", "guardian_greaves", "crimson_guard", "shiva_s_guard"]},
    "undying": {"*": ["arcane_boots", "solar_crest", "glimmer_cape", "pipe_of_insight", "aghanim_s_scepter"]},
    "ursa": {"1": ["phase_boots", "diffusal_blade", "black_king_bar", "basher_alt", "satanic", "abyssal_blade"],
              "_fix": []},
    "vengeful_spirit": {"*": ["urn_of_shadows", "arcane_boots", "solar_crest", "aghanim_s_scepter", "aether_lens"]},
    "venomancer": {"*": ["urn_of_shadows", "tranquil_boots", "spirit_vessel", "aghanim_s_shard", "aghanim_s_scepter", "shiva_s_guard"]},
    "viper": {"*": ["power_treads", "dragon_lance", "hurricane_pike", "black_king_bar", "skadi_alt", "butterfly"],
               "_fix": []},
    "visage": {"*": ["null_talisman", "boots_of_travel", "aghanim_s_scepter", "assault_cuirass", "sheepstick_alt"],
                "_fix": []},
    "void_spirit": {"*": ["null_talisman", "phase_boots", "echo_sabre", "aghanim_s_scepter", "octarine_core", "khanda"]},
    "warlock": {"*": ["arcane_boots", "holy_locket", "aghanim_s_scepter", "aghanim_s_shard", "refresher_orb"]},
    "weaver": {"1": ["power_treads", "maelstrom", "dragon_lance", "black_king_bar", "mjollnir", "greater_crit"],
                "*": ["urn_of_shadows", "spirit_vessel", "solar_crest", "aghanim_s_scepter", "black_king_bar"],
                "_fix": []},
    "windranger": {"*": ["null_talisman", "maelstrom", "monkey_king_bar", "black_king_bar", "gleipnir", "aghanim_s_scepter"]},
    "winter_wyvern": {"*": ["holy_locket", "glimmer_cape", "aether_lens", "aghanim_s_shard", "refresher_orb"]},
    "witch_doctor": {"*": ["glimmer_cape", "aether_lens", "aghanim_s_scepter", "aghanim_s_shard", "black_king_bar"]},
    "wraith_king": {"1": ["phase_boots", "armlet_of_mordiggian", "radiance", "blink_dagger", "assault_cuirass", "abyssal_blade"]},
    "zeus": {"*": ["null_talisman", "arcane_boots", "aghanim_s_shard", "aghanim_s_scepter", "octarine_core", "refresher_orb"]},
}

# Aliases for slugs that vary by dataset naming.
SLUG_ALIASES = {
    "greater_crit": "daedalus",
    "lesser_crit": "crystalys",
    "basher_alt": "skull_basher",
    "skadi_alt": "eye_of_skadi",
    "sheepstick_alt": "scythe_of_vyse",
}

# ---------------------------------------------------------------------------
# Generic phase templates keyed by (position bucket, attack_type/attribute).
# ---------------------------------------------------------------------------
STARTING = {
    "core_melee": ["tango", "quelling_blade", "gauntlets_of_strength", "iron_branch"],
    "core_ranged": ["tango", "slippers_of_agility", "circlet", "iron_branch"],
    "mid": ["tango", "faerie_fire", "mantle_of_intelligence", "iron_branch"],
    "offlane": ["tango", "quelling_blade", "ring_of_protection", "iron_branch"],
    "support": ["tango", "blood_grenade", "enchanted_mango", "clarity", "observer_ward"],
}
EARLY = {
    "core": ["magic_wand", "wraith_band", "boots_of_speed"],
    "str_core": ["magic_wand", "bracer", "boots_of_speed"],
    "int_core": ["magic_wand", "null_talisman", "boots_of_speed"],
    "support": ["magic_wand", "boots_of_speed", "infused_raindrops", "wind_lace"],
}
SITUATIONAL = {
    "core": ["black_king_bar", "monkey_king_bar", "nullifier", "linken_s_sphere",
             "satanic", "silver_edge", "heaven_s_halberd", "lotus_orb", "aeon_disk"],
    "support": ["glimmer_cape", "ghost_scepter", "force_staff", "eul_s_scepter_of_divinity",
                "lotus_orb", "aeon_disk", "spirit_vessel", "pipe_of_insight", "solar_crest"],
}

# ---------------------------------------------------------------------------
# Threat tags: auto-detected from ability text, plus curated overrides.
# tag -> (regex over ability name+description, human label)
# ---------------------------------------------------------------------------
TAG_PATTERNS: dict[str, str] = {
    "illusions": r"illusion",
    "summons": r"\bsummon|spiderling|wolves|golem|treant(?!\s*protector)|serpent ward|undead|skeleton|eidolon|familiar",
    "invisibility": r"invisib|conceal|vanish",
    "evasion": r"evasion|blur(?!red vision)|blind(?:s|ing)? .*miss|cause.*to miss",
    "silence": r"silenc",
    "hard_disable": r"\bstun|hex|taunt|forcing them to attack|sleep|fear\b|imprison|entomb",
    "root": r"\broot|ensnare|latch|tether.*enemy|leash",
    "big_magic": r"magical damage",
    "heal_regen": r"\bheal|regenerat|restor(?:e|ing) health|lifesteal|life steal",
    "mobility": r"teleport|blink|leap|dash|charges? (?:toward|at|to)|ball lightning|rolls?\b|phase",
    "physical_dps": None,  # curated / role-derived
    "armor_reduction": r"reduc\w* armor|armor reduction|corrosive",
    "mana_drain": r"mana burn|burn(?:s|ing)? mana|drain(?:s|ing)? mana",
    "break_worthy": None,  # curated
    "tanky": None,  # derived from stats/roles
    "slows": r"\bslow",
    "spell_reflect_dodge": r"spell shield|echo(?:es)? a targeted spell",
}

CURATED_EXTRA_TAGS: dict[str, list[str]] = {
    "phantom_assassin": ["evasion", "break_worthy", "physical_dps"],
    "bristleback": ["break_worthy", "tanky"],
    "spectre": ["break_worthy", "physical_dps"],
    "timbersaw": ["break_worthy", "tanky"],
    "alchemist": ["break_worthy", "tanky", "physical_dps"],
    "huskar": ["break_worthy", "heal_regen"],
    "necrophos": ["heal_regen", "break_worthy"],
    "viper": ["break_worthy"],
    "medusa": ["break_worthy", "tanky", "physical_dps"],
    "troll_warlord": ["physical_dps", "break_worthy"],
    "ursa": ["physical_dps", "break_worthy"],
    "sven": ["physical_dps"],
    "phantom_lancer": ["illusions", "physical_dps", "mana_drain"],
    "chaos_knight": ["illusions", "physical_dps"],
    "terrorblade": ["illusions", "physical_dps"],
    "naga_siren": ["illusions"],
    "anti_mage": ["mana_drain", "physical_dps", "mobility"],
    "slark": ["physical_dps", "break_worthy"],
    "faceless_void": ["physical_dps", "evasion", "break_worthy"],
    "juggernaut": ["physical_dps"],
    "drow_ranger": ["physical_dps", "break_worthy"],
    "sniper": ["physical_dps"],
    "templar_assassin": ["physical_dps", "break_worthy"],
    "clinkz": ["physical_dps", "invisibility"],
    "riki": ["invisibility", "physical_dps"],
    "bounty_hunter": ["invisibility"],
    "weaver": ["invisibility", "mobility"],
    "wraith_king": ["physical_dps", "reincarnation"],
    "lifestealer": ["physical_dps", "heal_regen"],
    "monkey_king": ["physical_dps"],
    "luna": ["physical_dps"],
    "gyrocopter": ["physical_dps"],
    "morphling": ["physical_dps", "tanky"],
    "slardar": ["armor_reduction"],
    "dazzle": ["heal_regen"],
    "oracle": ["heal_regen"],
    "omniknight": ["heal_regen"],
    "io": ["heal_regen"],
    "warlock": ["heal_regen", "summons"],
    "witch_doctor": ["heal_regen"],
    "abaddon": ["heal_regen"],
    "treant_protector": ["heal_regen", "invisibility"],
    "winter_wyvern": ["heal_regen"],
    "storm_spirit": ["mobility"],
    "ember_spirit": ["mobility"],
    "void_spirit": ["mobility"],
    "queen_of_pain": ["mobility"],
    "puck": ["mobility", "evasion"],
    "pudge": ["tanky"],
    "axe": ["tanky"],
    "centaur_warrunner": ["tanky"],
    "tidehunter": ["tanky"],
    "dragon_knight": ["tanky"],
    "wraith_king": ["physical_dps"],
    "meepo": ["summons"],
    "arc_warden": ["illusions"],
    "vengeful_spirit": ["illusions"],
    "broodmother": ["summons", "heal_regen"],
    "lycan": ["summons", "physical_dps"],
    "beastmaster": ["summons"],
    "nature_s_prophet": ["summons", "mobility"],
    "enigma": ["summons"],
    "visage": ["summons"],
    "chen": ["summons", "heal_regen"],
    "undying": ["summons", "tanky"],
    "brewmaster": ["summons", "evasion"],
    "zeus": ["big_magic"],
    "lina": ["big_magic"],
    "leshrac": ["big_magic"],
    "lion": ["big_magic"],
    "skywrath_mage": ["big_magic"],
    "tinker": ["big_magic"],
    "invoker": ["big_magic"],
    "kez": ["physical_dps"],
    "shadow_fiend": ["physical_dps", "big_magic"],
    "muerta": ["physical_dps"],
}

TAG_LABELS = {
    "illusions": "Illusions",
    "summons": "Summons",
    "invisibility": "Invisibility",
    "evasion": "Evasion / miss chance",
    "silence": "Silences",
    "hard_disable": "Hard disables (stun/hex/fear)",
    "root": "Roots",
    "big_magic": "Heavy magic damage",
    "heal_regen": "Healing / regen / lifesteal",
    "mobility": "High mobility",
    "physical_dps": "Physical damage carry",
    "armor_reduction": "Armor reduction",
    "mana_drain": "Mana burn / drain",
    "break_worthy": "Passive-reliant (Break target)",
    "tanky": "Very tanky",
    "slows": "Slows",
    "spell_reflect_dodge": "Spell block / echo",
    "reincarnation": "Reincarnation",
}

# tag -> counter items with reason, split by buyer role (core vs support).
COUNTER_RULES: dict[str, dict] = {
    "illusions": {
        "core": [("battle_fury", "Cleave melts illusions"), ("mjollnir", "Chain lightning clears illusion waves"),
                 ("gleipnir", "AoE root + chain lightning reveals the real hero")],
        "support": [("solar_crest", "Doesn't help vs illusions directly — armor the target instead")],
        "reason": "AoE damage instantly deletes illusions; single-target items are wasted on them.",
    },
    "summons": {
        "core": [("battle_fury", "Cleave clears summon armies"), ("maelstrom", "Chain lightning wipes summons"),
                 ("crimson_guard", "Damage block negates many small hits")],
        "support": [("mekansm", "AoE armor/heal vs summon chip damage")],
        "reason": "AoE damage and damage block neutralize summon-based pushing.",
    },
    "invisibility": {
        "core": [("gem_of_true_sight", "Permanent true sight"), ("monkey_king_bar", "You still need to hit them when revealed")],
        "support": [("dust_of_appearance", "Cheap on-demand reveal"), ("sentry_ward", "Area true sight for fights/wards"),
                    ("gem_of_true_sight", "Carry it once you have detection backup")],
        "reason": "Detection wins the game vs invisible heroes; never skip it.",
    },
    "evasion": {
        "core": [("monkey_king_bar", "True strike ignores evasion"), ("bloodthorn", "Silenced targets take guaranteed crits and can't be missed"),
                 ("witch_blade", "Early true-strike-adjacent magic damage")],
        "support": [("rod_of_atos", "Lock them down so spells do the killing")],
        "reason": "True strike or spell damage — don't right-click into evasion.",
    },
    "silence": {
        "core": [("black_king_bar", "Spell immunity beats silences"), ("manta_style", "Dispels silences"),
                 ("lotus_orb", "Dispel + reflect targeted silences")],
        "support": [("eul_s_scepter_of_divinity", "Self-dispel and disengage"), ("glimmer_cape", "Pre-cast before the silence lands"),
                    ("aeon_disk", "Survive locked-down bursts")],
        "reason": "Buy dispels and spell immunity so key spells still get cast.",
    },
    "hard_disable": {
        "core": [("black_king_bar", "Immune to most stuns/hexes"), ("linken_s_sphere", "Blocks the targeted initiation spell"),
                 ("manta_style", "Dodge projectiles / dispel")],
        "support": [("aeon_disk", "Survive the combo after the stun"), ("force_staff", "Save allies out of follow-up"),
                    ("glimmer_cape", "Save disabled allies")],
        "reason": "Spell immunity, spell block, and save items counter lockdown combos.",
    },
    "root": {
        "core": [("black_king_bar", "Most roots don't pierce immunity"), ("manta_style", "Dispels roots")],
        "support": [("eul_s_scepter_of_divinity", "Dispel roots on yourself"), ("force_staff", "Roots don't stop Force Staff — save rooted allies")],
        "reason": "Dispels remove roots; Force Staff still works while rooted.",
    },
    "big_magic": {
        "core": [("black_king_bar", "The classic answer to magic burst"), ("mage_slayer", "Magic resist + damage amp debuff"),
                 ("eternal_shroud", "Spell lifesteal + resistance for tanky cores")],
        "support": [("pipe_of_insight", "Team-wide magic barrier"), ("glimmer_cape", "+45% magic resist on demand"),
                    ("infused_raindrops", "Early nuke mitigation")],
        "reason": "Stack magic resistance and immunity before their burst timing hits.",
    },
    "heal_regen": {
        "core": [("skadi_alt", "Skadi reduces healing/lifesteal heavily"), ("shiva_s_guard", "AoE heal reduction aura")],
        "support": [("spirit_vessel", "75% heal reduction on a target"), ("urn_of_shadows", "Early build-up toward Vessel")],
        "reason": "Healing reduction turns sustain heroes into normal heroes.",
    },
    "mobility": {
        "core": [("gleipnir", "AoE root catches blinkers/dashers"), ("rod_of_atos", "Cheap root to lock them down"),
                 ("orchid_malevolence", "Silence stops escape spells"), ("basher_alt", "Bash interrupts mobility")],
        "support": [("rod_of_atos", "Root before they jump out"), ("scythe_of_vyse", "Instant hex — no escape")],
        "reason": "Roots, silences, and instant disables stop hit-and-run heroes.",
    },
    "physical_dps": {
        "core": [("assault_cuirass", "Armor for you, minus armor for them"), ("heaven_s_halberd", "Disarm the carry"),
                 ("butterfly", "Evasion vs right-clicks"), ("shiva_s_guard", "Armor + attack speed slow")],
        "support": [("ghost_scepter", "Immune to attacks for 4s"), ("solar_crest", "Armor an ally or shred the carry"),
                    ("glimmer_cape", "Break attack targeting")],
        "reason": "Armor, evasion, disarm, and ghost form blunt right-click damage.",
    },
    "armor_reduction": {
        "core": [("assault_cuirass", "Rebuild the armor they remove")],
        "support": [("mekansm", "AoE armor"), ("pavise", "Physical damage barrier on allies")],
        "reason": "Stack armor and barriers to offset the reduction.",
    },
    "mana_drain": {
        "core": [("black_king_bar", "Stops feedback-based burst engages"), ("linken_s_sphere", "Blocks Mana Void / targeted burn")],
        "support": [("arcane_boots", "Replenish drained mana"), ("aeon_disk", "Survive the mana-void timing")],
        "reason": "Keep mana topped up and block the big targeted payoff spell.",
    },
    "break_worthy": {
        "core": [("silver_edge", "Break disables their key passive"), ("bloodthorn", "Silence + amplified damage")],
        "support": [("spirit_vessel", "If the passive is regen-based, Vessel helps too")],
        "reason": "Break shuts off passive-dependent heroes almost entirely.",
    },
    "tanky": {
        "core": [("diffusal_blade", "Mana burn + slow scales vs big HP pools"), ("desolator", "Flat armor reduction"),
                 ("silver_edge", "Break their defensive passive"), ("skadi_alt", "Slow + stat shred on fat targets")],
        "support": [("solar_crest", "-armor makes your carry hit harder"), ("spirit_vessel", "% max HP damage")],
        "reason": "Percentage damage, armor reduction, and heal cut beat raw HP.",
    },
    "slows": {
        "core": [("black_king_bar", "Most slows don't pierce immunity"), ("sange_and_yasha", "Status resistance reduces slow duration")],
        "support": [("eul_s_scepter_of_divinity", "Dispel slows"), ("force_staff", "Reposition out of slow zones")],
        "reason": "Status resistance and dispels shrug off kiting.",
    },
    "spell_reflect_dodge": {
        "core": [("nullifier", "Mutes protective items; projectile isn't blocked by Linken's")],
        "support": [],
        "reason": "Pop spell block with a cheap spell first, or use items that ignore it.",
    },
    "reincarnation": {
        "core": [("diffusal_blade", "Burns the mana Reincarnation needs"), ("nullifier", "Keeps him killable through saves")],
        "support": [("spirit_vessel", "Cut his lifesteal sustain between deaths")],
        "reason": "Drain mana so Reincarnation can't trigger, or burst him twice fast.",
    },
    "invulnerable_saves": {"core": [], "support": [], "reason": ""},
}

BOOTS = {"power_treads", "phase_boots", "arcane_boots", "tranquil_boots", "boots_of_travel",
         "guardian_greaves", "boots_of_bearing", "boots_of_speed"}


def load_items() -> dict[str, dict]:
    idx = json.loads((ITEMS_DIR / "_index.json").read_text(encoding="utf-8"))
    return {it["slug"]: it for it in idx}


def load_heroes() -> list[dict]:
    heroes = []
    for f in sorted(HEROES_DIR.glob("*.json")):
        if f.name == "_index.json":
            continue
        heroes.append(json.loads(f.read_text(encoding="utf-8")))
    return heroes


def resolve(slug: str) -> str:
    return SLUG_ALIASES.get(slug, slug)


def positions_for(hero: dict) -> list[int]:
    slug = hero["slug"]
    if slug in POSITIONS:
        return POSITIONS[slug]
    roles = set(hero.get("roles", []))
    pos: list[int] = []
    if "Carry" in roles:
        pos.append(1)
    if "Nuker" in roles and hero.get("attack_type") == "Ranged":
        pos.append(2)
    if roles & {"Durable", "Initiator"}:
        pos.append(3)
    if "Support" in roles:
        pos += [4, 5]
    return sorted(set(pos)) or [4]


def auto_tags(hero: dict) -> list[str]:
    text = " ".join(
        f"{a.get('name','')} {a.get('description','')}" for a in hero.get("abilities", [])
    ).lower()
    tags = set()
    for tag, pat in TAG_PATTERNS.items():
        if pat and re.search(pat, text):
            tags.add(tag)
    tags.update(CURATED_EXTRA_TAGS.get(hero["slug"], []))
    if 1 in positions_for(hero) and hero.get("attack_type") == "Ranged":
        tags.add("physical_dps")
    stats = hero.get("stats", {})
    if stats.get("base_str", 0) >= 24 and stats.get("str_gain", 0) >= 3.0:
        tags.add("tanky")
    return sorted(tags)


def build_for(hero: dict, pos: int, items: dict) -> dict:
    slug = hero["slug"]
    attr = hero.get("primary_attribute", "str")
    melee = hero.get("attack_type") == "Melee"
    support = pos >= 4

    if support:
        starting = STARTING["support"]
        early = EARLY["support"]
    elif pos == 2:
        starting = STARTING["mid"] if attr in ("int", "universal") else (
            STARTING["core_melee"] if melee else STARTING["core_ranged"])
        early = EARLY["int_core"] if attr == "int" else EARLY["core"]
    elif pos == 3:
        starting = STARTING["offlane"]
        early = EARLY["str_core"]
    else:
        starting = STARTING["core_melee"] if melee else STARTING["core_ranged"]
        early = EARLY["core"]

    builds = CORE_BUILDS.get(slug, {})
    core = builds.get(str(pos)) or builds.get("*")
    if core is None:
        # generic fallback by role bucket
        if support:
            core = ["arcane_boots", "glimmer_cape", "force_staff", "aghanim_s_shard", "aghanim_s_scepter"]
        elif melee:
            core = ["power_treads", "echo_sabre", "black_king_bar", "basher_alt", "assault_cuirass"]
        else:
            core = ["power_treads", "dragon_lance", "black_king_bar", "hurricane_pike", "greater_crit"]
    core = [resolve(s) for s in core]

    situ = [s for s in (SITUATIONAL["support"] if support else SITUATIONAL["core"]) if s not in core]

    def pack(slugs):
        out = []
        for s in slugs:
            s = resolve(s)
            it = items.get(s)
            if it is None:
                raise SystemExit(f"Unknown item slug: {s} (hero {slug}, pos {pos})")
            out.append({"slug": s, "name": it["name"], "cost": it.get("cost")})
        return out

    return {
        "position": pos,
        "starting": pack(starting),
        "early": pack(early),
        "core": pack(core),
        "situational": pack(situ),
    }


def main():
    items = load_items()
    # validate curated tables up front
    for hero_slug, table in CORE_BUILDS.items():
        for key, lst in table.items():
            if key == "_fix":
                continue
            for s in lst:
                if resolve(s) not in items:
                    raise SystemExit(f"CORE_BUILDS bad slug {s!r} for {hero_slug}")
    for tag, rule in COUNTER_RULES.items():
        for side in ("core", "support"):
            for s, _reason in rule.get(side, []):
                if resolve(s) not in items:
                    raise SystemExit(f"COUNTER_RULES bad slug {s!r} in {tag}")

    heroes_out = []
    for hero in load_heroes():
        pos = positions_for(hero)
        tags = auto_tags(hero)
        heroes_out.append({
            "id": hero["id"],
            "name": hero["name"],
            "slug": hero["slug"],
            "attribute": hero.get("primary_attribute"),
            "attack_type": hero.get("attack_type"),
            "roles": hero.get("roles", []),
            "positions": pos,
            "threat_tags": tags,
            "builds": {str(p): build_for(hero, p, items) for p in pos},
        })

    counter_rules = {
        tag: {
            "label": TAG_LABELS.get(tag, tag),
            "reason": rule["reason"],
            "core": [{"slug": resolve(s), "name": items[resolve(s)]["name"],
                      "cost": items[resolve(s)].get("cost"), "why": why}
                     for s, why in rule.get("core", [])],
            "support": [{"slug": resolve(s), "name": items[resolve(s)]["name"],
                         "cost": items[resolve(s)].get("cost"), "why": why}
                        for s, why in rule.get("support", [])],
        }
        for tag, rule in COUNTER_RULES.items() if rule["reason"]
    }

    data = {
        "generated_from": "Valve dota2.com datafeed KB + curated itemization layer",
        "hero_count": len(heroes_out),
        "heroes": heroes_out,
        "tag_labels": TAG_LABELS,
        "counter_rules": counter_rules,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, indent=1), encoding="utf-8")
    OUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUT_JS.write_text("window.DOTA_APP_DATA = " + json.dumps(data) + ";\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON} and {OUT_JS}: {len(heroes_out)} heroes")


if __name__ == "__main__":
    main()
