import React, { useMemo, useState } from 'react';
import { Select } from '../ui/Select';
import { Input } from '../ui/Input';
import {
  getTnDistricts,
  getTnTaluks,
  getTnVillages,
  getTnDistrictCode,
  getTnTalukCode,
} from '../../utils/tnLocations';

export interface TnLocationSelectorProps {
  district: string;
  taluk?: string;
  village?: string;
  city?: string;
  onDistrictChange: (district: string, code?: string) => void;
  onTalukChange?: (taluk: string, code?: string) => void;
  onVillageChange?: (village: string) => void;
  onCityChange?: (city: string) => void;
  required?: boolean;
  disabled?: boolean;
  includeCity?: boolean;
  includeVillage?: boolean;
  layout?: 'grid-2' | 'grid-3' | 'grid-4' | 'stacked';
  className?: string;
}

export const TnLocationSelector: React.FC<TnLocationSelectorProps> = ({
  district,
  taluk = '',
  village = '',
  city = '',
  onDistrictChange,
  onTalukChange,
  onVillageChange,
  onCityChange,
  required = true,
  disabled = false,
  includeCity = true,
  includeVillage = true,
  layout = 'grid-2',
  className = '',
}) => {
  const districts = useMemo(() => getTnDistricts(), []);
  const taluks = useMemo(() => getTnTaluks(district), [district]);
  const villages = useMemo(() => getTnVillages(district, taluk), [district, taluk]);

  // Track if user explicitly selected custom input mode
  const [isCustomVillage, setIsCustomVillage] = useState<boolean>(() => {
    return Boolean(village && villages.length > 0 && !villages.includes(village));
  });

  const handleDistrictSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedDist = e.target.value;
    const code = getTnDistrictCode(selectedDist);
    onDistrictChange(selectedDist, code);

    // Auto-fill city to match district so user doesn't have to type it
    if (onCityChange) {
      onCityChange(selectedDist);
    }

    // Reset taluk and village when district changes
    if (onTalukChange) {
      onTalukChange('', undefined);
    }
    if (onVillageChange) {
      onVillageChange('');
    }
    setIsCustomVillage(false);
  };

  const handleTalukSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedTaluk = e.target.value;
    const code = getTnTalukCode(district, selectedTaluk);
    if (onTalukChange) {
      onTalukChange(selectedTaluk, code);
    }
    if (onVillageChange) {
      onVillageChange('');
    }
    setIsCustomVillage(false);
  };

  const handleVillageSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val === '__custom__') {
      setIsCustomVillage(true);
      if (onVillageChange) onVillageChange('');
    } else {
      setIsCustomVillage(false);
      if (onVillageChange) onVillageChange(val);
    }
  };

  const gridClass = useMemo(() => {
    switch (layout) {
      case 'grid-4':
        return 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3';
      case 'grid-3':
        return 'grid grid-cols-1 sm:grid-cols-3 gap-3';
      case 'stacked':
        return 'space-y-3';
      case 'grid-2':
      default:
        return 'grid grid-cols-1 sm:grid-cols-2 gap-3';
    }
  }, [layout]);

  return (
    <div className={`${gridClass} ${className}`}>
      {/* 1. District Dropdown */}
      <div>
        <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">
          District (TN) {required && <span className="text-red-500">*</span>}
        </label>
        <Select
          value={district}
          onChange={handleDistrictSelect}
          required={required}
          disabled={disabled}
        >
          <option value="">Select District (38 Districts)</option>
          {districts.map((d) => (
            <option key={d} value={d}>
              {d} {getTnDistrictCode(d) ? `(${getTnDistrictCode(d)})` : ''}
            </option>
          ))}
        </Select>
      </div>

      {/* 2. Taluk Dropdown */}
      <div>
        <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">
          Taluk {required && <span className="text-red-500">*</span>}
        </label>
        <Select
          value={taluk}
          onChange={handleTalukSelect}
          disabled={disabled || !district || taluks.length === 0}
        >
          <option value="">
            {!district
              ? 'Select District first'
              : taluks.length === 0
              ? 'No Taluks found'
              : `Select Taluk (${taluks.length} Taluks)`}
          </option>
          {taluks.map((t) => (
            <option key={t} value={t}>
              {t} {getTnTalukCode(district, t) ? `(${getTnTalukCode(district, t)})` : ''}
            </option>
          ))}
        </Select>
      </div>

      {/* 3. Village Dropdown */}
      {includeVillage && (
        <div>
          <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">
            Revenue Village {required && <span className="text-red-500">*</span>}
            {villages.length > 0 && (
              <span className="ml-1 text-[10px] text-gray-500 font-normal">
                ({villages.length} Villages)
              </span>
            )}
          </label>

          {!isCustomVillage ? (
            <Select
              value={village}
              onChange={handleVillageSelect}
              disabled={disabled || !taluk || villages.length === 0}
            >
              <option value="">
                {!taluk
                  ? 'Select Taluk first'
                  : villages.length === 0
                  ? 'No villages found'
                  : `Select Village (${villages.length} Villages)`}
              </option>

              {/* If current village isn't in this taluk's list (e.g. existing property data), display it */}
              {village && !villages.includes(village) && (
                <option value={village}>{village} (Current)</option>
              )}

              {villages.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}

              <option value="__custom__">+ Other / Enter Custom Locality...</option>
            </Select>
          ) : (
            <div className="flex items-center gap-1.5">
              <Input
                value={village}
                onChange={(e) => onVillageChange && onVillageChange(e.target.value)}
                placeholder="Type custom locality/area"
                required={required}
                disabled={disabled}
                className="text-xs"
                autoFocus
              />
              <button
                type="button"
                onClick={() => setIsCustomVillage(false)}
                className="text-[11px] text-[var(--color-forest)] underline shrink-0 hover:opacity-80"
                title="Back to dropdown"
              >
                Dropdown
              </button>
            </div>
          )}
        </div>
      )}

      {/* 4. City / Town (auto-filled from District) */}
      {includeCity && onCityChange && (
        <div>
          <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">
            City / Corporation {required && <span className="text-red-500">*</span>}
          </label>
          <Input
            value={city || district}
            onChange={(e) => onCityChange(e.target.value)}
            placeholder="Auto-set from District"
            required={required}
            disabled={disabled}
            className="text-xs bg-gray-50"
          />
        </div>
      )}
    </div>
  );
};
