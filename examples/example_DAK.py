import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly from the standing_katz_DAK module file
from material_balance.standing_katz_DAK import calculate_Z_from_real_conditions

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Exemplo de uso prático:")
    print("="*60)
    
    # Exemplo 2: Cálculo a partir de condições reais
    # Dados para um gás natural típico
    P = 20  # atm
    T = 524   # °K (Kelvin)
    Ppc = 36.30  # atm (pseudocrítico)
    Tpc = 436.50  # °K (pseudocrítico)
    
    Ppr, Tpr, Z = calculate_Z_from_real_conditions(P, T, Ppc, Tpc)
    
    print(f"Pressão real: {P} psia")
    print(f"Temperatura real: {T} °R")
    print(f"Pressão pseudocrítica: {Ppc} psia")
    print(f"Temperatura pseudocrítica: {Tpc} °R")
    print(f"→ Pressão pseudoreduzida (Ppr): {Ppr:.3f}")
    print(f"→ Temperatura pseudoreduzida (Tpr): {Tpr:.3f}")
    print(f"→ Fator de compressibilidade (Z): {Z:.4f}")
    
    # Verificar com diferentes condições
 #   print("\n" + "-"*40)
 #   print("Variação de Z com diferentes Ppr:")
    
 #   Tpr_fixed = 1.5
 #   for Ppr_test in [0.5, 1.0, 2.0, 3.0, 5.0]:
 #       Z_test = Z_StandingKatz_DAK(Ppr_test, Tpr_fixed)
 #        print(f"  Ppr = {Ppr_test:.1f}, Tpr = {Tpr_fixed:.1f} → Z = {Z_test:.4f}")