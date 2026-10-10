"""The test benches: one station per group of mechanical combinations.

A bench is a static grid with a floor at y = 0, a projector and a battery. Every
mechanical base stands on the floor, or on the payload of another subgrid, and
gets its top part from the game's own "add top part" action when the fixtures
are generated (fixtures.py). Each top part carries `payload` armor blocks
stacked along its up axis, the blocks MGP has to weld onto the subgrid after
it has created the head.

The vanilla combinations come from the game's CubeBlocks definitions (bases with
their TopPart groups); DLC blocks are left out, the test clients run without
Steam.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Combo:
    name: str
    base_type: str
    base: str
    action: str
    head: str
    # Armor blocks stacked on the head, in the head's grid size
    payload: int = 1
    # Bases mounted on top of the payload, each with a subgrid of its own
    children: list["Combo"] = field(default_factory=list)
    # Orientation of the base in its grid; hinges mount with their right side
    up: str = "Up"
    # Where it stands on its bench, set by Bench
    min: tuple[int, int, int] = (0, 0, 0)


@dataclass
class Bench:
    name: str
    size: str
    combos: list[Combo]
    # Cells between two bases on the floor
    spacing: int = 5
    columns: int = 8
    # Armor blocks to weld on the bench's own grid, besides the bases
    armor: list[tuple[int, int, int]] = field(default_factory=list)

    def __post_init__(self):
        for i, combo in enumerate(self.combos):
            row, column = divmod(i, self.columns)
            combo.min = (2 + column * self.spacing, 1, 3 + row * self.spacing)

    @property
    def floor(self) -> list[tuple[int, int, int]]:
        """A strip along x for the projector and the battery, and a column
        from it to a 3 by 3 pad under every base"""
        columns = min(len(self.combos), self.columns)
        cells = {(x, 0, z) for x in range(columns * self.spacing) for z in (0, 1)}
        for combo in self.combos:
            mx, _, mz = combo.min
            cells |= {(mx, 0, z) for z in range(mz)}
            cells |= {(x, 0, z) for x in range(mx, mx + 3) for z in range(mz, mz + 3)}
        return sorted(cells)


def _rotor(name, base_type, base, action, head, payload=1, children=()):
    up = "Right" if "Hinge" in base else "Up"
    return Combo(name, base_type, base, action, head, payload, list(children), up)


LARGE = Bench(
    "large",
    "Large",
    [
        _rotor("rotor", "MotorStator", "LargeStator", "AddRotorTopPart", "LargeRotor"),
        _rotor(
            "rotor-small-head",
            "MotorStator",
            "LargeStator",
            "AddSmallRotorTopPart",
            "SmallRotor",
        ),
        _rotor(
            "advanced-rotor",
            "MotorAdvancedStator",
            "LargeAdvancedStator",
            "AddRotorTopPart",
            "LargeAdvancedRotor",
        ),
        _rotor(
            "advanced-rotor-small-head",
            "MotorAdvancedStator",
            "LargeAdvancedStator",
            "AddSmallRotorTopPart",
            "SmallAdvancedRotorSmall",
        ),
        _rotor(
            "hinge",
            "MotorAdvancedStator",
            "LargeHinge",
            "AddHingeTopPart",
            "LargeHingeHead",
        ),
        _rotor(
            "hinge-small-head",
            "MotorAdvancedStator",
            "LargeHinge",
            "AddSmallHingeTopPart",
            "SmallHingeHead",
        ),
        _rotor(
            "piston",
            "ExtendedPistonBase",
            "LargePistonBase",
            "Add Top Part",
            "LargePistonTop",
        ),
    ],
    columns=4,
)

SMALL = Bench(
    "small",
    "Small",
    [
        _rotor("rotor", "MotorStator", "SmallStator", "AddRotorTopPart", "SmallRotor"),
        _rotor(
            "advanced-rotor-3x3",
            "MotorAdvancedStator",
            "SmallAdvancedStator",
            "AddRotorTopPart",
            "SmallAdvancedRotor",
        ),
        _rotor(
            "advanced-rotor",
            "MotorAdvancedStator",
            "SmallAdvancedStatorSmall",
            "AddRotorTopPart",
            "SmallAdvancedRotorSmall",
        ),
        _rotor(
            "hinge-3x3",
            "MotorAdvancedStator",
            "MediumHinge",
            "AddHingeTopPart",
            "MediumHingeHead",
        ),
        _rotor(
            "hinge",
            "MotorAdvancedStator",
            "SmallHinge",
            "AddHingeTopPart",
            "SmallHingeHead",
        ),
        _rotor(
            "piston",
            "ExtendedPistonBase",
            "SmallPistonBase",
            "Add Top Part",
            "SmallPistonTop",
        ),
    ],
    spacing=8,
)


def _suspensions(prefix: str) -> list[Combo]:
    combos = []
    for kind in ("", "Short"):
        for size in ("1x1", "2x2", "3x3", "5x5"):
            for mirrored in ("", "mirrored"):
                if mirrored and size == "2x2":
                    mirrored = "Mirrored"
                subtype = f"{prefix}{kind}Suspension{size}{mirrored}"
                wheel = "RealWheel" + ("" if size == "3x3" else size) + mirrored
                if prefix:
                    wheel = "Small" + wheel
                name = f"suspension-{kind.lower() or 'normal'}-{size}" + (
                    "-mirrored" if mirrored else ""
                )
                combos.append(
                    Combo(name, "MotorSuspension", subtype, "Add Top Part", wheel, 0)
                )
    return combos


WHEELS_LARGE = Bench("wheels-large", "Large", _suspensions(""), spacing=7, columns=4)
WHEELS_SMALL = Bench(
    "wheels-small", "Small", _suspensions("Small"), spacing=12, columns=4
)

# Subgrids on subgrids: a hinge carrying a piston carrying a rotor, and a rotor
# head carrying two pistons side by side
CHAIN = Bench(
    "chain",
    "Large",
    [
        _rotor(
            "hinge-piston-rotor",
            "MotorAdvancedStator",
            "LargeHinge",
            "AddHingeTopPart",
            "LargeHingeHead",
            children=[
                _rotor(
                    "piston",
                    "ExtendedPistonBase",
                    "LargePistonBase",
                    "Add Top Part",
                    "LargePistonTop",
                    children=[
                        _rotor(
                            "rotor",
                            "MotorStator",
                            "LargeStator",
                            "AddRotorTopPart",
                            "LargeRotor",
                        )
                    ],
                )
            ],
        ),
        _rotor(
            "rotor-two-pistons",
            "MotorAdvancedStator",
            "LargeAdvancedStator",
            "AddRotorTopPart",
            "LargeAdvancedRotor",
            children=[
                _rotor(
                    "piston-a",
                    "ExtendedPistonBase",
                    "LargePistonBase",
                    "Add Top Part",
                    "LargePistonTop",
                ),
                _rotor(
                    "piston-b",
                    "ExtendedPistonBase",
                    "LargePistonBase",
                    "Add Top Part",
                    "LargePistonTop",
                ),
            ],
        ),
    ],
    spacing=8,
)

# Toolbars and block references across a subgrid, see refs.py. The spacing
# makes the floor strip long enough for the station's row of blocks.
REFS = Bench(
    "refs",
    "Large",
    [_rotor("rotor", "MotorStator", "LargeStator", "AddRotorTopPart", "LargeRotor", 3)],
    spacing=14,
)

# A hand built mechanical group with references across four levels of
# subgrids, copied from a test world by import_group.py, not generated
GROUP = Bench("group", "Large", [])

# Welded in survival by ship welders fed from cargo containers, see
# survival.py. The armor block on the strip is the one a welder on a piston
# reaches into (GitHub issue #136).
SURVIVAL = Bench(
    "survival",
    "Large",
    [
        _rotor("rotor", "MotorStator", "LargeStator", "AddRotorTopPart", "LargeRotor"),
        _rotor(
            "piston",
            "ExtendedPistonBase",
            "LargePistonBase",
            "Add Top Part",
            "LargePistonTop",
        ),
    ],
    spacing=8,
    columns=2,
    armor=[(4, 1, 1)],
)

BENCHES = {
    b.name: b
    for b in (LARGE, SMALL, WHEELS_LARGE, WHEELS_SMALL, CHAIN, REFS, GROUP, SURVIVAL)
}
