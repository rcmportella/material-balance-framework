import math

def Z_StandingKatz_DAK(Ppr, Tpr, tol=1e-12, max_iter=100):
    """
    Calcula o fator de compressibilidade Z usando a correlação Dranchuk-Abou-Kassem (DAK).
    
    Parâmetros:
    -----------
    Ppr : float
        Pressão pseudoreduzida (adimensional)
    Tpr : float
        Temperatura pseudoreduzida (adimensional)
    tol : float, opcional
        Tolerância para convergência (padrão: 1e-12)
    max_iter : int, opcional
        Número máximo de iterações (padrão: 100)
    
    Retorna:
    --------
    float
        Fator de compressibilidade Z
    
    Levanta:
    --------
    Exception
        Se não convergir em max_iter iterações
    """
    # Constantes da correlação DAK
    A1 = 0.3265
    A2 = -1.0700
    A3 = -0.5339
    A4 = 0.01569
    A5 = -0.05165
    A6 = 0.5475
    A7 = -0.7361
    A8 = 0.1844
    
    # Chute inicial para Z (gás ideal + ajuste)
    Z = 1.0
    
    for i in range(max_iter):
        # 1. Calcular densidade reduzida
        rho_r = 0.27 * Ppr / (Z * Tpr)
        
        # 2. Calcular os termos da função f(Z)
        T1 = (A1 + A2/Tpr + A3/(Tpr**3)) * rho_r
        T2 = (A4 + A5/Tpr) * (rho_r**2)
        T3 = (A5 * A6 * rho_r**5) / Tpr
        T4_num = A7 * rho_r**2 * (1 + A8 * rho_r**2)
        T4_den = Tpr**3
        T4_exp = math.exp(-A8 * rho_r**2)
        T4 = (T4_num / T4_den) * T4_exp
        
        # Função f(Z) = Z - [1 + T1 + T2 + T3 + T4]
        f_Z = Z - (1 + T1 + T2 + T3 + T4)
        
        # 3. Calcular a derivada df/dZ ANALITICAMENTE
        # d(rho_r)/dZ = -0.27 * Ppr / (Tpr * Z^2) = -rho_r / Z
        drho_r_dZ = -rho_r / Z
        
        # Derivadas de cada termo em relação a rho_r
        dT1_drho = A1 + A2/Tpr + A3/(Tpr**3)
        dT2_drho = 2 * (A4 + A5/Tpr) * rho_r
        dT3_drho = (5 * A5 * A6 * rho_r**4) / Tpr
        dT4_drho_num = A7 * (2*rho_r + 4*A8*rho_r**3)
        dT4_drho = (dT4_drho_num / T4_den) * T4_exp - (T4_num / T4_den) * A8 * 2 * rho_r * T4_exp
        
        # Derivada total usando regra da cadeia: df/dZ = 1 - dF/drho_r * drho_r/dZ
        # onde F = 1 + T1 + T2 + T3 + T4
        dF_drho = dT1_drho + dT2_drho + dT3_drho + dT4_drho
        df_dZ = 1 - dF_drho * drho_r_dZ
        
        # 4. Atualizar Z usando Newton-Raphson
        Z_new = Z - f_Z / df_dZ
        
        # 5. Verificar convergência
        if abs(Z_new - Z) < tol:
            return Z_new
        
        Z = Z_new
    
    raise Exception(f"Não convergiu após {max_iter} iterações. Último Z = {Z}")

# Função alternativa com derivada numérica (para comparação)
def Z_DAK_numerical_derivative(Ppr, Tpr, tol=1e-12, max_iter=100):
    """
    Versão com derivada numérica (menos eficiente, mas útil para verificação)
    """
    A1, A2, A3 = 0.3265, -1.0700, -0.5339
    A4, A5, A6 = 0.01569, -0.05165, 0.5475
    A7, A8 = -0.7361, 0.1844
    
    Z = 1.0
    h = 1e-8  # Pequeno incremento para derivada numérica
    
    for i in range(max_iter):
        # Função f(Z)
        rho_r = 0.27 * Ppr / (Z * Tpr)
        T1 = (A1 + A2/Tpr + A3/(Tpr**3)) * rho_r
        T2 = (A4 + A5/Tpr) * (rho_r**2)
        T3 = (A5 * A6 * rho_r**5) / Tpr
        T4 = (A7 * rho_r**2 * (1 + A8 * rho_r**2) / (Tpr**3)) * math.exp(-A8 * rho_r**2)
        f_Z = Z - (1 + T1 + T2 + T3 + T4)
        
        # Derivada numérica df/dZ
        # f(Z + h)
        rho_r_h = 0.27 * Ppr / ((Z + h) * Tpr)
        T1_h = (A1 + A2/Tpr + A3/(Tpr**3)) * rho_r_h
        T2_h = (A4 + A5/Tpr) * (rho_r_h**2)
        T3_h = (A5 * A6 * rho_r_h**5) / Tpr
        T4_h = (A7 * rho_r_h**2 * (1 + A8 * rho_r_h**2) / (Tpr**3)) * math.exp(-A8 * rho_r_h**2)
        f_Z_h = (Z + h) - (1 + T1_h + T2_h + T3_h + T4_h)
        
        df_dZ_num = (f_Z_h - f_Z) / h
        
        # Atualizar Z
        Z_new = Z - f_Z / df_dZ_num
        
        if abs(Z_new - Z) < tol:
            return Z_new
        
        Z = Z_new
    
    raise Exception(f"Não convergiu após {max_iter} iterações")

# Função para testar e comparar ambas as implementações
def test_DAK_implementation():
    """Testa a implementação com valores conhecidos"""
    
    # Valores de teste (Ppr, Tpr, Z_esperado aproximado)
    test_cases = [
        (1.0, 1.5, 0.920),  # Condições moderadas
        (3.0, 1.1, 0.620),  # Alta pressão, baixa temperatura
        (0.5, 2.0, 0.970),  # Baixa pressão, alta temperatura
        (2.0, 1.5, 0.860),  # Condições intermediárias
    ]
    
    print("Teste da correlação DAK (Dranchuk-Abou-Kassem)")
    print("=" * 60)
    
    for Ppr, Tpr, Z_expected in test_cases:
        try:
            Z_analytic = Z_StandingKatz_DAK(Ppr, Tpr)
            Z_numeric = Z_DAK_numerical_derivative(Ppr, Tpr)
            
            print(f"Ppr = {Ppr:.2f}, Tpr = {Tpr:.2f}:")
            print(f"  Z (derivada analítica) = {Z_analytic:.6f}")
            print(f"  Z (derivada numérica)  = {Z_numeric:.6f}")
            print(f"  Diferença = {abs(Z_analytic - Z_numeric):.2e}")
            print(f"  Esperado ≈ {Z_expected:.3f}")
            print()
            
        except Exception as e:
            print(f"Erro para Ppr={Ppr}, Tpr={Tpr}: {e}")
            print()

# Exemplo de uso prático
def calculate_Z_from_real_conditions(P, T, Ppc, Tpc):
    """
    Calcula Z a partir de condições reais usando DAK
    
    Parâmetros:
    -----------
    P : float
        Pressão real (psia, kPa, etc.)
    T : float
        Temperatura real (R, K, etc.)
    Ppc : float
        Pressão pseudocrítica
    Tpc : float
        Temperatura pseudocrítica
    
    Retorna:
    --------
    tuple : (Ppr, Tpr, Z)
    """
    Ppr = P / Ppc
    Tpr = T / Tpc
    
    Z = Z_StandingKatz_DAK(Ppr, Tpr)
    
    return Ppr, Tpr, Z

# Exemplo 1: Teste básico
if __name__ == "__main__":
    # Testar as implementações
    test_DAK_implementation()
    
    print("\n" + "="*60)
    print("Exemplo de uso prático:")
    print("="*60)
    
    # Exemplo 2: Cálculo a partir de condições reais
    # Dados para um gás natural típico
    P = 2000  # psia
    T = 600   # °R (Rankine)
    Ppc = 667  # psia (pseudocrítico)
    Tpc = 375  # °R (pseudocrítico)
    
    Ppr, Tpr, Z = calculate_Z_from_real_conditions(P, T, Ppc, Tpc)
    
    print(f"Pressão real: {P} psia")
    print(f"Temperatura real: {T} °R")
    print(f"Pressão pseudocrítica: {Ppc} psia")
    print(f"Temperatura pseudocrítica: {Tpc} °R")
    print(f"→ Pressão pseudoreduzida (Ppr): {Ppr:.3f}")
    print(f"→ Temperatura pseudoreduzida (Tpr): {Tpr:.3f}")
    print(f"→ Fator de compressibilidade (Z): {Z:.4f}")
    
    # Verificar com diferentes condições
    print("\n" + "-"*40)
    print("Variação de Z com diferentes Ppr:")
    
    Tpr_fixed = 1.5
    for Ppr_test in [0.5, 1.0, 2.0, 3.0, 5.0]:
        Z_test = Z_StandingKatz_DAK(Ppr_test, Tpr_fixed)
        print(f"  Ppr = {Ppr_test:.1f}, Tpr = {Tpr_fixed:.1f} → Z = {Z_test:.4f}")