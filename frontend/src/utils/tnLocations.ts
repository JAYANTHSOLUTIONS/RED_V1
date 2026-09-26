import tnData from '../data/tnAdministrativeData.json';

export interface TnAdministrativeStructure {
  districts: string[];
  districtCodes: Record<string, string>;
  talukCodes: Record<string, string>;
  hierarchy: Record<string, Record<string, string[]>>;
}

const data = tnData as TnAdministrativeStructure;

/**
 * Returns list of all 38 official districts in Tamil Nadu.
 */
export function getTnDistricts(): string[] {
  return data.districts;
}

/**
 * Returns official taluks for a given Tamil Nadu district.
 */
export function getTnTaluks(district?: string): string[] {
  if (!district || !data.hierarchy[district]) {
    return [];
  }
  return Object.keys(data.hierarchy[district]);
}

/**
 * Returns revenue villages for a given district and taluk.
 */
export function getTnVillages(district?: string, taluk?: string): string[] {
  if (!district || !taluk || !data.hierarchy[district] || !data.hierarchy[district][taluk]) {
    return [];
  }
  return data.hierarchy[district][taluk];
}

/**
 * Returns the official revenue code for a district.
 */
export function getTnDistrictCode(district?: string): string | undefined {
  if (!district) return undefined;
  return data.districtCodes[district];
}

/**
 * Returns the official revenue code for a taluk.
 */
export function getTnTalukCode(district?: string, taluk?: string): string | undefined {
  if (!district || !taluk) return undefined;
  return data.talukCodes[`${district}:${taluk}`];
}
