import uuid
from datetime import datetime
from typing import Optional, List, Literal, Union, Annotated

import requests
from pydantic import BaseModel, Field

base_api_url: str = "https://api.gbif.org/v1"

class QueryResult[T](BaseModel):
    offset: int
    limit: int
    endOfRecords: bool
    count: Optional[int] = Field(None)
    results: List[T]

class ApiVernacularName(BaseModel):
    taxonKey: Optional[int] = Field(None)
    vernacularName: str
    language: Optional[str] = Field(None)
    lifeStage: Optional[str] = Field(None)
    sex: Optional[str] = Field(None)
    country: Optional[str] = Field(None)
    area: Optional[str] = Field(None)
    source: Optional[str] = Field(None)
    sourceTaxonKey: Optional[int] = Field(None)
    preferred: Optional[bool] = Field(None)
    plural: Optional[bool] = Field(None)

class ApiBaseNameUsage(BaseModel):
    key: int
    nubKey: Optional[int] = Field(None)
    nameKey: Optional[int] = Field(None)
    taxonID: Optional[str] = Field(None)
    sourceTaxonKey: Optional[int] = Field(None)
    kingdom: Optional[str] = Field(None)
    phylum: Optional[str] = Field(None)
    order: Optional[str] = Field(None)
    family: Optional[str] = Field(None)
    genus: Optional[str] = Field(None)
    subgenus: Optional[str] = Field(None)
    species: Optional[str] = Field(None)
    kingdomKey: Optional[int] = Field(None)
    phylumKey: Optional[int] = Field(None)
    classKey: Optional[int] = Field(None)
    orderKey: Optional[int] = Field(None)
    familyKey: Optional[int] = Field(None)
    genusKey: Optional[int] = Field(None)
    subgenusKey: Optional[int] = Field(None)
    speciesKey: Optional[int] = Field(None)
    datasetKey: uuid.UUID
    constituentKey: Optional[uuid.UUID] = Field(None)
    parentKey: Optional[int] = Field(None)
    parent: Optional[str] = Field(None)
    proParteKey: Optional[int] = Field(None)
    acceptedKey: Optional[int] = Field(None)
    accepted: Optional[str] = Field(None)
    basionymKey: Optional[int] = Field(None)
    basionym: Optional[str] = Field(None)
    scientificName: str
    canonicalName: Optional[str] = Field(None)
    authorship: Optional[str] = Field(None)
    nameType: Optional[str] = Field(None)
    origin: str
    taxonomicStatus: Optional[str] = Field(None)
    nomenclaturalStatus: Optional[List[str]] = Field(None)
    remarks: Optional[str] = Field(None)
    publishedIn: Optional[str] = Field(None)
    accordingTo: Optional[str] = Field(None)
    numDescendants: Optional[int] = Field(None)
    references: Optional[str] = Field(None)
    modified: Optional[datetime] = Field(None)
    deleted: Optional[datetime] = Field(None)
    lastCrawled: Optional[datetime] = Field(None)
    lastInterpreted: Optional[datetime] = Field(None)
    issues: List[str]
    clazz: Optional[str] = Field(None, alias="class")

class ApiSpeciesNameUsage(ApiBaseNameUsage):
    rank: Literal["SPECIES"]

class ApiSubspeciesNameUsage(ApiBaseNameUsage):
    rank: Literal["SUBSPECIES"]

class ApiVarietyNameUsage(ApiBaseNameUsage):
    rank: Literal["VARIETY"]

class ApiUnrankedNameUsage(ApiBaseNameUsage):
    rank: Literal["UNRANKED"]

ApiNameUsage = Annotated[Union[ApiSpeciesNameUsage, ApiSubspeciesNameUsage, ApiVarietyNameUsage, ApiUnrankedNameUsage], Field(discriminator="rank")]

class ApiParsedName(BaseModel):
    key: Optional[int] = Field(None)
    scientificName: Optional[str] = Field(None)
    type: Optional[str] = Field(None)
    genusOrAbove: Optional[str] = Field(None)
    infraGeneric: Optional[str] = Field(None)
    specificEpithet: Optional[str] = Field(None)
    infraSpecificEpithet: Optional[str] = Field(None)
    cultivarEpithet: Optional[str] = Field(None)
    strain: Optional[str] = Field(None)
    notho: Optional[str] = Field(None)
    authorship: Optional[str] = Field(None)
    year: Optional[str] = Field(None)
    bracketAuthorship: Optional[str] = Field(None)
    bracketYear: Optional[str] = Field(None)
    sensu: Optional[str] = Field(None)
    parsed: Optional[bool] = Field(None)
    parsedPartially: Optional[bool] = Field(None)
    nomStatus: Optional[str] = Field(None)
    remarks: Optional[str] = Field(None)
    canonicalName: Optional[str] = Field(None)
    canonicalNameWithMarker: Optional[str] = Field(None)
    canonicalNameComplete: Optional[str] = Field(None)
    rankMarker: Optional[str] = Field(None)

def get_vernacular_name_response(taxon_id: int) -> QueryResult[ApiVernacularName]:
    url = f"{base_api_url}/species/{taxon_id}/vernacularNames"
    response = requests.get(url)
    response.raise_for_status()
    return QueryResult[ApiVernacularName].model_validate(response.json())

def get_synonyms_response(taxon_id: int) -> QueryResult[ApiNameUsage]:
    url = f"{base_api_url}/species/{taxon_id}/synonyms"
    response = requests.get(url)
    response.raise_for_status()
    return QueryResult[ApiNameUsage].model_validate(response.json())

def get_children_response(taxon_id: int) -> QueryResult[ApiNameUsage]:
    url = f"{base_api_url}/species/{taxon_id}/children"
    response = requests.get(url)
    response.raise_for_status()
    return QueryResult[ApiNameUsage].model_validate(response.json())

def get_name_response(taxon_id: int) -> ApiParsedName:
    url = f"{base_api_url}/species/{taxon_id}/name"
    response = requests.get(url)
    response.raise_for_status()
    return ApiParsedName.model_validate(response.json())
