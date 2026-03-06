"""DNA::}{::lang – Declarative organism specification language parser.

DNA::}{::lang provides a declarative specification language for defining
distributed agents, optimization objectives, invariants, and safety rules.

Example organism specification::

    organism QA11dSH {
        mesh z3braMesh dimension=11
        runtime targets = [linux, android, browser]
        agents {
            discovery
            simulation
            verifier
            orchestrator
        }
        domain healthcare_digital_twin
    }

Use :func:`parse_organism` to parse a spec string and obtain an
:class:`OrganismSpec` dataclass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MeshSpec:
    """Specification for the z3braMesh."""

    name: str = "z3braMesh"
    dimension: int = 11


@dataclass
class OrganismSpec:
    """Parsed representation of a DNA::}{::lang organism block.

    Attributes
    ----------
    name : str
        The organism identifier.
    mesh : MeshSpec
        Mesh configuration.
    runtime_targets : list[str]
        Target runtime environments (e.g. ``["linux", "android", "browser"]``).
    agents : list[str]
        Agent types declared within the organism.
    domain : str
        Application domain (e.g. ``"healthcare_digital_twin"``).
    invariants : list[str]
        Safety / correctness invariants declared in the spec.
    raw : dict[str, Any]
        All other key–value pairs parsed from the organism body.
    """

    name: str = ""
    mesh: MeshSpec = field(default_factory=MeshSpec)
    runtime_targets: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    domain: str = ""
    invariants: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_organism(spec: str) -> OrganismSpec:
    """Parse a DNA::}{::lang organism specification string.

    Parameters
    ----------
    spec : str
        The text of an organism definition block.

    Returns
    -------
    OrganismSpec
        Populated organism specification.

    Raises
    ------
    ValueError
        If the ``organism`` keyword and name are missing.
    """
    spec = spec.strip()

    # Extract organism name
    name_match = re.search(r"\borganism\s+(\w+)", spec)
    if not name_match:
        raise ValueError("No 'organism <Name>' declaration found in spec.")
    organism_name = name_match.group(1)

    result = OrganismSpec(name=organism_name)

    # Extract mesh block:  mesh <name> dimension=<n>
    mesh_match = re.search(r"\bmesh\s+(\w+)(?:\s+dimension\s*=\s*(\d+))?", spec)
    if mesh_match:
        result.mesh = MeshSpec(
            name=mesh_match.group(1),
            dimension=int(mesh_match.group(2)) if mesh_match.group(2) else 11,
        )

    # Extract runtime targets:  runtime targets = [a, b, c]
    rt_match = re.search(r"\bruntime\s+targets\s*=\s*\[([^\]]*)\]", spec)
    if rt_match:
        result.runtime_targets = [
            t.strip() for t in rt_match.group(1).split(",") if t.strip()
        ]

    # Extract agents block:  agents { ... }
    agents_match = re.search(r"\bagents\s*\{([^}]*)\}", spec, re.DOTALL)
    if agents_match:
        result.agents = [
            a.strip()
            for a in re.split(r"[\n,]+", agents_match.group(1))
            if a.strip()
        ]

    # Extract domain:  domain <value>
    domain_match = re.search(r"\bdomain\s+(\S+)", spec)
    if domain_match:
        result.domain = domain_match.group(1)

    # Extract invariant declarations:  invariant <text>
    result.invariants = re.findall(r"\binvariant\s+(.+)", spec)

    return result


def render_organism(spec: OrganismSpec) -> str:
    """Render an :class:`OrganismSpec` back to DNA::}{::lang source text.

    Parameters
    ----------
    spec : OrganismSpec
        Specification to render.

    Returns
    -------
    str
        A DNA::}{::lang organism definition string.
    """
    lines: list[str] = [f"organism {spec.name} {{"]

    lines.append(f"  mesh {spec.mesh.name} dimension={spec.mesh.dimension}")

    if spec.runtime_targets:
        targets = ", ".join(spec.runtime_targets)
        lines.append(f"  runtime targets = [{targets}]")

    if spec.agents:
        lines.append("  agents {")
        for agent in spec.agents:
            lines.append(f"      {agent}")
        lines.append("  }")

    if spec.domain:
        lines.append(f"  domain {spec.domain}")

    for inv in spec.invariants:
        lines.append(f"  invariant {inv}")

    lines.append("}")
    return "\n".join(lines)
