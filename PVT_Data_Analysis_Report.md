# Comprehensive PVT Data Analysis and Empirical Validation Report

This report summarizes the comparison between experimental laboratory PVT data and standard empirical industry correlations (Standing, Hall-Yarborough, Beggs-Robinson, and Lee-Gonzalez-Eakin) at a reservoir temperature of 180 °F.

## 1. Input Reservoir Fluid Properties
* **Reservoir Temperature (T):** 180 °F (639.67 °R)
* **Measured Bubble Point Pressure (P_b):** 2,500 psia
* **Stock Tank Oil Gravity:** 35 °API (Specific gravity γ_o = 0.850)
* **Gas Specific Gravity (γ_g):** 0.65 (Molecular weight M_g = 18.83 lb/lb-mol)

---

## 2. Laboratory Data Profile
The laboratory profile across varying pressures at 180 °F serves as our primary baseline:

| Pressure (P, psia) | Solution GOR (R_s, scf/STB) | Oil FVF (B_o, bbl/STB) | Oil Viscosity (μ_o, cP) |
| :--- | :--- | :--- | :--- |
| 4,000 (Undersaturated) | 850 (at P_b) | 1.250 | 1.15 |
| 3,000 (Undersaturated) | 850 (at P_b) | 1.265 | 1.05 |
| **2,500 (Bubble Point)** | **850** | **1.280** | **0.95** |
| 1,800 (Saturated) | 600 | 1.180 | 1.25 |
| 1,000 (Saturated) | 320 | 1.090 | 1.60 |

---

## 3. Empirical Validation at Bubble Point Pressure (2,500 psia)

### 3.1 Bubble Point Pressure Calculation (Standing Correlation)
Using Standing's forward calculation to solve for P_b given R_s = 850 scf/STB:
* **Temperature & Gravity Factor (a):**
  a = 0.00091(180) - 0.0125(35) = -0.2737
* **Standing Formula:**
  P_b = 18.2 * [ (850 / 0.65)^0.83 * 10^-0.2737 - 1.4 ] = 3,716.24 psia

### 3.2 Summary of Fluid Properties Comparison

| Property | Selected Empirical Method | Calculated Value | Lab Measured | % Deviation |
| :--- | :--- | :--- | :--- | :--- |
| **Bubble Point (P_b)** | Standing (1947) | **3,716.24 psia** | 2,500.00 psia | +48.65% |
| **Solution GOR (R_s)** | Standing (1947) @ 2500 psi | **529.33 scf/STB** | 850.00 scf/STB | -37.73% |
| **Oil FVF (B_o)** | Standing (1947) @ 2500 psi | **1.4461 bbl/STB** | 1.2800 bbl/STB | +12.98% |
| **Gas FVF (B_g)** | Real Gas Law (Z=0.9802) | **0.00709 bbl/scf** | *Not Measured* | N/A |
| **Oil Viscosity (μ_o)** | Beggs-Robinson / Chew-Connally | **0.4733 cP** | 0.9500 cP | -50.18% |
| **Gas Viscosity (μ_g)** | Lee-Gonzalez-Eakin (1966) | **0.01718 cP** | *Not Measured* | N/A |

---

## 4. Engineering QA/QC Conclusions
1. **Regional Discrepancies:** Standing's correlation severely overpredicts bubble point pressure (+48.65%) and overpredicts oil swelling (B_o). This occurs because Standing's datasets were calibrated primarily on California crude oils.
2. **Viscosity Mismatch:** The empirical dead-oil and live-oil corrections significantly underestimate the actual oil viscosity (-50.18%).
3. **Recommended Next Steps:** Before deploying this data into a reservoir simulator, the empirical coefficients of these models must be adjusted (tuned) using multi-variable regression or non-linear optimization to minimize statistical error against the experimental lab values.
