"""
Retrieval engine — multi-collection semantic search with metadata
filtering and cross-collection re-ranking.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from src.core.config import LIBRARIES, LIBRARY_ORDER
from src.core.embedder import embed_query
from src.core.vector_store import search as vector_search

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass
class RetrievedChunk:
    """A single retrieved chunk with metadata and score."""
    text: str
    score: float  # cosine similarity (1 - distance)
    library: str
    source_file: str
    page_number: int
    title: str = ""
    chunk_index: int = 0

    @property
    def citation(self) -> str:
        """Human-readable citation string."""
        lib_name = LIBRARIES.get(self.library, {}).get("name", self.library)
        return f"[{lib_name}] {self.source_file}, p.{self.page_number}"


@dataclass
class RetrievalResult:
    """Result container for a retrieval operation."""
    query: str
    chunks: list  # list of RetrievedChunk
    libraries_searched: list  # list of str
    total_candidates: int = 0


# ── Library routing ──────────────────────────────────────────────────────

# Keywords → libraries mapping for smart routing
_KEYWORD_ROUTES = {
    # ── RCW: Revised Code of Washington (state statutes) ─────────────
    "rcw_chapters": [
        # Direct references
        r"\bRCW\b", r"\brevised code\b", r"\bstate statute\b",
        r"\bstate law\b", r"\bwashington law\b", r"\bwashington state law\b",
        # Criminal law (Title 9, 9A, 10)
        r"\bhomicide\b", r"\bassault\b", r"\bburglary\b", r"\btheft\b",
        r"\brobbery\b", r"\bfraud\b", r"\bsex offense\b", r"\bharassment\b",
        r"\bkidnapping\b", r"\barson\b", r"\btrespass\b", r"\bfelony\b",
        r"\bmisdemeanor\b",
        # Family law (Title 26)
        r"\bmarriage\b", r"\bdissolution\b", r"\bdivorce\b", r"\bchild support\b",
        r"\bchild custody\b", r"\badoption\b", r"\bparentage\b", r"\bvisitation\b",
        r"\bfamily court\b", r"\bcommunity property\b",
        # Vehicles & DUI (Title 46)
        r"\bDUI\b", r"\bDWI\b", r"\bdriver.s license\b", r"\bvehicle registration\b",
        r"\btraffic violation\b", r"\bblood alcohol\b", r"\bmotor vehicle\b",
        r"\bfinancial responsibility\b",
        # Workers compensation (Title 51)
        r"\bworkers.? compensation\b", r"\bindustrial insurance\b",
        r"\bworkplace injury\b", r"\boccupational\b",
        # Landlord-tenant (Title 59)
        r"\blandlord\b", r"\btenant\b", r"\beviction\b", r"\brental\b",
        r"\blease\b", r"\btenancy\b", r"\bmobile home park\b",
        r"\bmanufactured home\b",
        # Environment (Title 70A, 90)
        r"\bwater pollution\b", r"\bwater rights\b", r"\bclean air\b",
        r"\bhazardous waste\b", r"\bsolid waste\b", r"\benvironmental cleanup\b",
        r"\bshoreline management\b",
        # Business & corporations (Title 23B, 24, 25)
        r"\bcorporation\b", r"\bLLC\b", r"\bpartnership\b",
        r"\bsecurities\b", r"\bbusiness registration\b",
        # Real property (Title 58, 61, 64)
        r"\breal estate\b", r"\bproperty deed\b", r"\bmortgage\b",
        r"\bforeclosure\b", r"\bhomestead\b", r"\bcondominium\b",
        r"\bseller disclosure\b",
        # Insurance (Title 48)
        r"\binsurance regulation\b", r"\binsurance commissioner\b",
        # Education (Title 28A, 28B, 28C)
        r"\bschool district\b", r"\bhigher education\b", r"\btuition\b",
        r"\bscholarship\b", r"\bvocational education\b",
        # Alcohol & cannabis (Title 66, 69)
        r"\bliquor\b", r"\bcannabis\b", r"\bmarijuana\b",
        r"\bcontrolled substance\b",
        # Health (Title 70, 71)
        r"\bmental health\b", r"\bpublic health\b", r"\bhospital\b",
        # Employment (Title 49, 50)
        r"\bunemployment\b", r"\bwage\b", r"\bminimum wage\b",
        r"\bpaid leave\b", r"\bdiscrimination\b",
        # Probate & trusts (Title 11)
        r"\bprobate\b", r"\btrust\b", r"\bestate\b", r"\bwill\b",
        r"\bguardianship\b",
        # Consumer protection (Title 19)
        r"\bconsumer protection\b", r"\bunfair business\b", r"\bdeceptive\b",
    ],

    # ── WAC: Washington Administrative Code (agency regulations) ─────
    "wac_chapters": [
        # Direct references
        r"\bWAC\b", r"\badministrative code\b", r"\bagency rule\b",
        r"\bstate regulation\b", r"\badministrative regulation\b",
        # Ecology / Environment (Title 173)
        r"\bDepartment of Ecology\b", r"\bEcology\b",
        r"\bgroundwater\b", r"\bwater quality\b", r"\bair quality\b",
        r"\bsediment\b", r"\bwetland\b", r"\bfloodplain\b",
        r"\bSEPA\b", r"\bshoreline\b", r"\bstormwater permit\b",
        r"\bwater discharge\b", r"\bNPDES\b",
        # Health (Title 246)
        r"\bDepartment of Health\b", r"\bDOH\b",
        r"\bcommunicable disease\b", r"\bimmunization\b",
        r"\bfood service\b", r"\brestaurant inspection\b",
        r"\bdrinking water\b", r"\bseptic\b", r"\bon-site sewage\b",
        r"\bradiation\b", r"\blaboratory\b",
        r"\bnursing license\b", r"\bpharmacy\b", r"\bphysician\b",
        r"\bdentist\b", r"\boptometrist\b", r"\bchiropract\b",
        r"\bcredential\b",
        # Social & health services (Title 388)
        r"\bDSHS\b", r"\bDepartment of Social\b",
        r"\badult family home\b", r"\bnursing home\b",
        r"\blong-term care\b", r"\bresidential care\b",
        r"\bchild welfare\b", r"\bchild protective\b",
        r"\badult protective\b", r"\bbackground check\b",
        r"\bfoster care\b", r"\bdevelopmental disabilit\b",
        # Labor & Industries (Title 296)
        r"\bL&I\b", r"\bLabor and Industries\b",
        r"\bworkplace safety\b", r"\bOSHA\b", r"\bWISHA\b",
        r"\bprevailing wage\b", r"\bapprenticeship\b",
        r"\bcontractor registration\b", r"\belectrical\b",
        r"\bplumbing\b", r"\belevator\b", r"\bboiler\b",
        r"\bcrane\b", r"\basbestos\b", r"\blead\b",
        # Education (Title 180, 181, 392)
        r"\bOSPI\b", r"\bteacher certification\b",
        r"\bschool funding\b", r"\bspecial education\b",
        r"\bstudent discipline\b", r"\bschool bus\b",
        # Employment security (Title 192)
        r"\bunemployment insurance\b", r"\bunemployment benefit\b",
        r"\bjob search\b", r"\bclaim filing\b",
        # Insurance (Title 284)
        r"\binsurance commissioner\b", r"\binsurance regulation\b",
        r"\bhealth carrier\b", r"\blife insurance\b",
        r"\bcredit insurance\b",
        # Liquor & Cannabis (Title 314)
        r"\bliquor and cannabis board\b", r"\bliquor license\b",
        r"\bcannabis license\b", r"\bmarijuana license\b",
        # Transportation (Title 468)
        r"\bWSDOT\b", r"\bhighway\b", r"\bferr(?:y|ies)\b",
        r"\btoll\b",
        # Revenue (Title 458)
        r"\bproperty tax\b", r"\bsales tax\b", r"\bexcise tax\b",
        r"\breal estate excise\b",
        # Licensing (Title 308)
        r"\bdriver license\b", r"\bvehicle title\b",
        r"\bnotary\b",
        # Fish & Wildlife (Title 220)
        r"\bhunting\b", r"\bfishing license\b", r"\bwildlife\b",
        r"\bfish and wildlife\b",
        # Agriculture (Title 16)
        r"\bfood inspection\b", r"\bpesticide\b", r"\banimal health\b",
        r"\bdairy\b", r"\borganic\b",
    ],

    # ── SMC: Seattle Municipal Code (city ordinances) ────────────────
    "smc_chapters": [
        # Direct references
        r"\bSMC\b", r"\bseattle municipal\b", r"\bcity code\b",
        r"\bcity ordinance\b", r"\bseattle code\b", r"\bseattle ordinance\b",
        # Title-specific topics
        r"\bseattle .*(tax|revenue|fee)\b", r"\bseattle election\b",
        r"\bseattle business\b", r"\bseattle animal\b",
        r"\bseattle noise\b", r"\bseattle parking\b",
        r"\bseattle traffic\b", r"\bseattle street\b",
        r"\bseattle sidewalk\b", r"\bseattle park\b",
        r"\bseattle human rights\b", r"\bseattle discrimination\b",
        r"\bseattle labor\b", r"\bseattle wage\b",
        r"\bseattle utility\b", r"\bseattle sewer\b",
        r"\bseattle water rate\b",
        r"\bseattle criminal\b", r"\bseattle harbor\b",
        # Land use (Title 23 — the big one)
        r"\bseattle zoning\b", r"\bseattle land use\b",
        r"\bseattle density\b", r"\bseattle setback\b",
        r"\bseattle height limit\b", r"\bFAR\b",
        r"\bseattle permitting\b",
        # Building (Title 22)
        r"\bseattle building\b", r"\bseattle construction\b",
        r"\bseattle demolition\b",
        # Environment (Title 25)
        r"\bseattle environment\b", r"\bseattle historic\b",
        r"\bseattle landmark\b", r"\bseattle tree\b",
    ],

    # ── IBC: International Building Codes (WA amendments) ────────────
    "ibc_wa_docs": [
        # Direct references
        r"\bIBC\b", r"\bIRC\b", r"\bIMC\b", r"\bIFC\b", r"\bIECC\b",
        r"\binternational building code\b", r"\binternational fire code\b",
        r"\binternational mechanical code\b", r"\binternational residential code\b",
        r"\binternational energy\b", r"\bwildland.urban interface\b",
        # Topics
        r"\bbuilding code\b", r"\bfire code\b", r"\bmechanical code\b",
        r"\benergy code\b", r"\bresidential code\b",
        r"\boccupancy classification\b", r"\bfire rating\b",
        r"\bfire resistance\b", r"\bfire separation\b",
        r"\bfire sprinkler\b", r"\bfire alarm\b",
        r"\begress\b", r"\bmeans of egress\b", r"\bexit\b",
        r"\boccupant load\b", r"\btype.of.construction\b",
        r"\bfire wall\b", r"\bfire barrier\b",
        r"\bstructural load\b", r"\bwind load\b", r"\bseismic\b",
        r"\bsnow load\b", r"\benergy efficiency\b",
        r"\binsulation\b", r"\bHVAC\b", r"\bventilation\b",
        r"\bplumbing fixture\b", r"\baccessibility\b", r"\bADA\b",
    ],

    # ── SPU Design Standards (Seattle Public Utilities) ──────────────
    "spu_design_standards": [
        # Direct references
        r"\bSPU\b", r"\bseattle public utilities\b",
        r"\bdesign standard\b", r"\bdesign criteria\b",
        # Infrastructure topics
        r"\bpump station\b", r"\bcathodic\b", r"\bcathodic protection\b",
        r"\bSCADA\b", r"\binstrumentation\b", r"\bcontrol system\b",
        r"\bwater main\b", r"\bwater service\b", r"\bwater infrastructure\b",
        r"\bpipe material\b", r"\bductile iron\b",
        r"\bdrainage system\b", r"\bwastewater\b", r"\bsewer system\b",
        r"\bsewer design\b", r"\bcombined sewer\b", r"\bCSO\b",
        r"\belectrical design\b", r"\bswitchgear\b", r"\btransformer\b",
        r"\bphysical security\b", r"\baccess control\b",
        r"\bdevelopment services\b", r"\bside sewer\b",
        r"\bhydraulic model\b", r"\bsystem modeling\b",
        r"\bdesign construction\b", r"\bpermitting\b",
        r"\benvironmental review\b",
    ],

    # ── Seattle DIR Rules (Director's Rules) ─────────────────────────
    "seattle_dir_rules": [
        # Direct references
        r"\bDIR\b", r"\bdirector.s rule\b", r"\bSDCI\b", r"\bDCLU\b",
        # Topics from actual rule titles
        r"\bRRIO\b", r"\brental registration\b", r"\brental inspection\b",
        r"\btenant relocation\b", r"\brelocation assistance\b",
        r"\bdesign review\b", r"\bdesign guideline\b",
        r"\blight rail\b", r"\bstreetscape\b", r"\bstreet concept\b",
        r"\bgreen factor\b", r"\blandscaping requirement\b",
        r"\btree protection\b", r"\btree replacement\b",
        r"\bbuilding valuation\b", r"\bfee schedule\b",
        r"\bpin pile\b", r"\baugercast\b", r"\bshotcrete\b",
        r"\bconcrete mix\b", r"\bsteel fabricat\b",
        r"\bsprinkler system\b", r"\bfire alarm inspection\b",
        r"\belevator machinery\b", r"\bhoistway\b",
        r"\bseismic design\b", r"\blateral force\b",
        r"\bshear wall\b", r"\bover.?height building\b",
        r"\bfloodplain development\b", r"\bshoreline district\b",
        r"\bsolar collector\b", r"\benergy modeling\b",
        r"\befficiency dwelling\b", r"\bsmall efficiency\b",
        r"\btransitional encampment\b",
        r"\bMaster Use Permit\b", r"\bMUP\b",
        r"\bseattle permit\b",
        r"\bacoustic\b", r"\bamplified sound\b", r"\bnighttime noise\b",
        r"\bhistoric preservation\b",
    ],

    # ── WA Governor Executive Orders ─────────────────────────────────
    "wa_governor_orders": [
        # Direct references
        r"\bexecutive order\b", r"\bgovernor\b", r"\bgovernor.s order\b",
        # Topics from actual orders
        r"\breproductive health\b", r"\baffordable housing crisis\b",
        r"\bhousing task force\b", r"\bimmigrant\b", r"\bimmigration\b",
        r"\bfamily separation\b",
        r"\bdata center\b", r"\bcustomer experience\b",
        r"\bproject labor agreement\b", r"\bFAFSA\b",
        r"\btribal nation\b", r"\bsovereign\b",
        r"\bclean energy\b", r"\benergy tax credit\b",
        r"\bpermitting process\b", r"\blicensing process\b",
        r"\bstate agency\b", r"\bstate operation\b",
    ],

    # ── Washington Court Opinions ────────────────────────────────────
    "washington_court_opinions": [
        # Direct references
        r"\bcourt opinion\b", r"\bcourt of appeals\b",
        r"\bsupreme court\b", r"\bappellate\b",
        r"\bjudgment\b", r"\bruling\b", r"\bprecedent\b",
        # Case citations
        r"\bv\.\b", r"\bState v\b", r"\bCity of .+ v\b",
        r"\bplaintiff\b", r"\bdefendant\b", r"\bpetitioner\b",
        r"\brespondent\b", r"\bappellant\b",
        # Legal procedure
        r"\bsummary judgment\b", r"\bcertiorari\b",
        r"\bdismiss(?:al|ed)\b", r"\bremand\b", r"\brevers(?:al|ed)\b",
        r"\baffirm(?:ed)?\b", r"\bdissent\b", r"\bconcurrence\b",
        r"\bjury\b", r"\btrial court\b",
        r"\bliability\b", r"\bdamages\b", r"\bdue process\b",
        r"\bconstitutional\b",
        # Specific courts & agencies
        r"\bDep.?t of .+\b",
    ],
}


def detect_relevant_libraries(query: str) -> list:
    """
    Detect which libraries are most relevant to a query based on keywords.
    Returns a list of library keys, or all libraries if no match.
    """
    query_lower = query.lower()
    matched = []

    for lib_key, patterns in _KEYWORD_ROUTES.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                if lib_key not in matched:
                    matched.append(lib_key)
                break

    return matched if matched else list(LIBRARY_ORDER)


# ── Core retrieval ───────────────────────────────────────────────────────


def retrieve(
    query: str,
    libraries: Optional[list] = None,
    top_k: int = 10,
    per_library_k: int = 10,
    where: Optional[dict] = None,
    auto_route: bool = True,
    min_score: float = 0.0,
) -> RetrievalResult:
    """
    Search across one or more ChromaDB collections and return
    re-ranked results.

    Args:
        query:          Natural language search query.
        libraries:      Explicit list of library keys to search.
                        If None, auto-detects based on query keywords.
        top_k:          Number of final results to return after re-ranking.
        per_library_k:  Number of candidates to pull from each collection.
        where:          ChromaDB metadata filter (applied to every collection).
        auto_route:     If True and libraries is None, uses keyword routing.
                        If False and libraries is None, searches all.
        min_score:      Minimum cosine similarity to include (0.0 = no filter).

    Returns:
        RetrievalResult with ranked chunks and metadata.
    """
    # Determine which libraries to search
    if libraries:
        search_libs = libraries
    elif auto_route:
        search_libs = detect_relevant_libraries(query)
    else:
        search_libs = list(LIBRARY_ORDER)

    # Validate library keys
    search_libs = [k for k in search_libs if k in LIBRARIES]
    if not search_libs:
        logger.warning("No valid libraries to search")
        return RetrievalResult(query=query, chunks=[], libraries_searched=[])

    # Embed the query once
    query_vec = embed_query(query)

    # Search each collection and collect candidates
    all_chunks = []
    total_candidates = 0

    for lib_key in search_libs:
        try:
            results = vector_search(
                collection_name=lib_key,
                query_embedding=query_vec,
                n_results=per_library_k,
                where=where,
            )

            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]

            for doc, meta, dist in zip(docs, metas, dists):
                score = 1.0 - dist  # cosine distance → similarity
                if score < min_score:
                    continue

                chunk = RetrievedChunk(
                    text=doc,
                    score=score,
                    library=meta.get("library", lib_key),
                    source_file=meta.get("source_file", ""),
                    page_number=meta.get("page_number", 0),
                    title=meta.get("title", ""),
                    chunk_index=meta.get("chunk_index", 0),
                )
                all_chunks.append(chunk)
                total_candidates += 1

        except Exception as e:
            logger.error("Search failed for collection '%s': %s", lib_key, e)

    # Re-rank: sort by score descending, take top_k
    all_chunks.sort(key=lambda c: c.score, reverse=True)
    ranked = all_chunks[:top_k]

    # Deduplicate: if same source_file + page appear multiple times, keep best
    seen = set()
    deduped = []
    for chunk in ranked:
        key = (chunk.source_file, chunk.page_number, chunk.text[:100])
        if key not in seen:
            seen.add(key)
            deduped.append(chunk)

    logger.info(
        "Retrieved %d chunks from %d libraries (query: '%s')",
        len(deduped), len(search_libs), query[:60],
    )

    return RetrievalResult(
        query=query,
        chunks=deduped,
        libraries_searched=search_libs,
        total_candidates=total_candidates,
    )


def retrieve_with_context(
    query: str,
    top_k: int = 5,
    max_context_chars: int = 8000,
    **kwargs,
) -> str:
    """
    Retrieve chunks and format them as a context string for an LLM prompt.

    Args:
        query:              Search query.
        top_k:              Number of chunks to include.
        max_context_chars:  Maximum total characters in the context block.

    Returns:
        Formatted context string with citations.
    """
    result = retrieve(query, top_k=top_k, **kwargs)

    if not result.chunks:
        return "No relevant documents found."

    context_parts = []
    total_chars = 0

    for i, chunk in enumerate(result.chunks, start=1):
        citation = chunk.citation
        entry = f"[Source {i}] {citation}\n{chunk.text}\n"

        if total_chars + len(entry) > max_context_chars:
            break

        context_parts.append(entry)
        total_chars += len(entry)

    return "\n---\n".join(context_parts)


def format_results_table(result: RetrievalResult) -> str:
    """Format retrieval results as a readable table string."""
    lines = [
        f"Query: \"{result.query}\"",
        f"Libraries searched: {', '.join(result.libraries_searched)}",
        f"Total candidates: {result.total_candidates}",
        f"Results returned: {len(result.chunks)}",
        "─" * 70,
    ]

    for i, chunk in enumerate(result.chunks, start=1):
        lines.append(
            f"  [{i}]  score={chunk.score:.4f}  | {chunk.citation}"
        )
        snippet = chunk.text[:200].replace("\n", " ")
        lines.append(f"       {snippet}...")
        lines.append("")

    return "\n".join(lines)
