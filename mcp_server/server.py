"""Serveur MCP exposant deux outils, accessible en streamable-http."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-server", host="0.0.0.0", port=24000)

EMPLOYES = {
    "mohamed": {"nom": "Mohamed", "poste": "Développeur", "salaire": 23000, "anciennete": 12},
    "sara": {"nom": "Sara", "poste": "Data Scientist", "salaire": 18000, "anciennete": 4},
    "yassine": {"nom": "Yassine", "poste": "Chef de projet", "salaire": 27000, "anciennete": 9},
}


@mcp.tool()
def get_employee_infos(nom: str) -> dict:
    """Renvoie le poste, le salaire (en MAD) et l'ancienneté (en années) d'un employé à partir de son nom."""
    return EMPLOYES.get(nom.lower(), {"erreur": f"Aucun employé nommé {nom}"})


@mcp.tool()
def calculer_prime(salaire: float, anciennete: int) -> dict:
    """Calcule la prime annuelle d'un employé : 5 % du salaire par tranche de 5 ans d'ancienneté (max 20 %)."""
    taux = min(anciennete // 5 * 5, 20)
    return {"taux_pourcent": taux, "prime_mad": round(salaire * taux / 100, 2)}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")