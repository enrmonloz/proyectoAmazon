% =========================================================================
% ANÁLISIS ECONÓMICO: REDISEÑO LAYOUT SVQ1 + DQA4
% Máster en Ingeniería Industrial – DPCIS 2025-26
%
% Todos los datos numéricos proceden del enunciado del proyecto.
% Secciones referenciadas: §3 (costes actuales), §4 (opciones inversión),
% §6 (RRHH), §7 (infraestructura), §8 (riesgos).
% =========================================================================
clear; clc; close all;

fprintf('=========================================================\n');
fprintf('   ANÁLISIS ECONÓMICO – REDISEÑO LAYOUT SVQ1 + DQA4\n');
fprintf('=========================================================\n\n');


% =========================================================================
% BLOQUE 1 – SITUACIÓN ACTUAL (AS-IS)
% Fuente: §3.1 y §3.2 del enunciado
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 1 · COSTES ACTUALES (dos centros separados)\n');
fprintf('─────────────────────────────────────────────────────────\n');

% Costes operativos anuales por concepto (Tabla 1 del enunciado)
coste_personal_svq1    = 20.7e6;   % € – Personal SVQ1
coste_personal_dqa4    =  9.1e6;   % € – Personal DQA4
coste_energia_svq1     =  6.2e6;   % € – Energía/combustible SVQ1
coste_energia_dqa4     =  4.7e6;   % € – Energía/combustible DQA4
coste_instalac_svq1    =  2.4e6;   % € – Instalaciones SVQ1
coste_instalac_dqa4    =  1.5e6;   % € – Instalaciones DQA4
coste_otros_svq1       =  7.0e6;   % € – Otros gastos SVQ1
coste_otros_dqa4       =  2.8e6;   % € – Otros gastos DQA4
coste_transferencias   =  1.99e6;  % € – Transporte SVQ1→DQA4 (26.100 paq/día · 25 km · 365 días)

coste_total_svq1 = coste_personal_svq1 + coste_energia_svq1 + ...
                   coste_instalac_svq1  + coste_otros_svq1;          % = 36,3 M€
coste_total_dqa4 = coste_personal_dqa4 + coste_energia_dqa4 + ...
                   coste_instalac_dqa4  + coste_otros_dqa4;           % = 18,1 M€
coste_total_actual = coste_total_svq1 + coste_total_dqa4 + coste_transferencias;

fprintf('  Personal total:           %8.2f M€\n', (coste_personal_svq1 + coste_personal_dqa4)/1e6);
fprintf('  Energía/combustible:      %8.2f M€\n', (coste_energia_svq1  + coste_energia_dqa4 )/1e6);
fprintf('  Instalaciones:            %8.2f M€\n', (coste_instalac_svq1 + coste_instalac_dqa4)/1e6);
fprintf('  Otros gastos:             %8.2f M€\n', (coste_otros_svq1    + coste_otros_dqa4   )/1e6);
fprintf('  Transferencias redundantes:%7.2f M€  ← INEFICIENCIA CLAVE\n', coste_transferencias/1e6);
fprintf('  ─────────────────────────────────────────\n');
fprintf('  COSTE TOTAL ACTUAL:       %8.2f M€/año\n\n', coste_total_actual/1e6);

% Datos de volumen relevantes
paquetes_svq1_dia   = 125000;  % unidades/día procesadas en SVQ1
paquetes_dqa4_dia   =  38900;  % paquetes/día entregados por DQA4
transferencias_dia  =  26100;  % paq/día que viajan entre centros (67% de DQA4)
distancia_km        =     25;  % km entre SVQ1 y DQA4
coste_paq_transfer  = coste_transferencias / (transferencias_dia * 365);

fprintf('  Volumen diario SVQ1:      %6d unidades/día\n',  paquetes_svq1_dia);
fprintf('  Volumen diario DQA4:      %6d paquetes/día\n',  paquetes_dqa4_dia);
fprintf('  Transferencias diarias:   %6d paquetes/día  (%.0f%% de DQA4)\n', ...
        transferencias_dia, 100*transferencias_dia/paquetes_dqa4_dia);
fprintf('  Distancia entre centros:  %6d km\n',            distancia_km);
fprintf('  Coste unitario transfer:  %7.4f €/paquete\n\n', coste_paq_transfer);


% =========================================================================
% BLOQUE 2 – DESGLOSE DE AHORROS POSIBLES
% Fuente: §4.3 del enunciado
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 2 · ORIGEN DE LOS AHORROS ANUALES\n');
fprintf('─────────────────────────────────────────────────────────\n');

% Cada partida con su rango mínimo/máximo según enunciado
%                                   min (M€)   max (M€)
ahorro_transferencias_min = 1.99e6; % fijo     fijo     – 100% garantizado
ahorro_transferencias_max = 1.99e6;
ahorro_personal_min       = 2.4e6;  % rango del enunciado
ahorro_personal_max       = 4.1e6;
ahorro_energia_min        = 1.6e6;  % rango del enunciado
ahorro_energia_max        = 2.3e6;
ahorro_instalacion_min    = 0.7e6;  % rango del enunciado (cierre nave DQA4)
ahorro_instalacion_max    = 1.5e6;

ahorro_total_min = ahorro_transferencias_min + ahorro_personal_min + ...
                   ahorro_energia_min + ahorro_instalacion_min;   % = 6,69 M€ ≈ 6,7 M€
ahorro_total_max = ahorro_transferencias_max + ahorro_personal_max + ...
                   ahorro_energia_max + ahorro_instalacion_max;   % = 9,89 M€ ≈ 9,9 M€

fprintf('  Partida                         Mín (M€)   Máx (M€)   Certeza\n');
fprintf('  ──────────────────────────────────────────────────────────────\n');
fprintf('  Eliminar transferencias SVQ1→DQA4  %5.2f      %5.2f     100%% garantizado\n', ...
        ahorro_transferencias_min/1e6, ahorro_transferencias_max/1e6);
fprintf('  Reducción personal duplicado       %5.2f      %5.2f     Alta\n', ...
        ahorro_personal_min/1e6, ahorro_personal_max/1e6);
fprintf('  Reducción energía/combustible      %5.2f      %5.2f     Alta\n', ...
        ahorro_energia_min/1e6, ahorro_energia_max/1e6);
fprintf('  Cierre nave DQA4 (12.500 m²)       %5.2f      %5.2f     Media\n', ...
        ahorro_instalacion_min/1e6, ahorro_instalacion_max/1e6);
fprintf('  ──────────────────────────────────────────────────────────────\n');
fprintf('  AHORRO TOTAL ANUAL                 %5.2f      %5.2f     M€/año\n\n', ...
        ahorro_total_min/1e6, ahorro_total_max/1e6);

% Nota: valor residual de DQA4 (dato puntual del enunciado §7.1)
valor_residual_dqa4 = 523000;  % € – se pierde al cerrar si no se gestiona
fprintf('  Valor residual nave DQA4 (§7.1):   %.0f €  (recuperable en negociación)\n\n', ...
        valor_residual_dqa4);


% =========================================================================
% BLOQUE 3 – CLASIFICACIÓN COMPLETA DE COSTES ADICIONALES DEL PROYECTO
% Fuente: §6.2, §6.3, §6.4, §8.3 del enunciado
%
% CRITERIO DE CLASIFICACIÓN (finanzas de proyectos):
%   · CAPEX:  desembolso único ligado a la puesta en marcha (año 0 o 1)
%   · OPEX:   coste recurrente INCREMENTAL causado por la unificación
%   · Excluir: costes que ocurren igualmente sin el proyecto (§6.3)
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 3 · CLASIFICACIÓN DE TODOS LOS COSTES ADICIONALES\n');
fprintf('─────────────────────────────────────────────────────────\n');

% ── A. FORMACIÓN (§6.4) ───────────────────────────────────────────────────
% Pago único en año 0. No se repite. → CAPEX diferido
capex_formacion = 1.56e6;   % €

% ── B. REGULACIÓN LABORAL 2025 (§6.3) ────────────────────────────────────
% Afecta a SVQ1 y DQA4 independientemente de la decisión.
% Coste incremental del proyecto = 0 €. → EXCLUIR del análisis
opex_regulacion_2025 = 3.25e6;   % €/año – solo documentado, no incluido
% Si NO unificas: pagas 3,25 M€/año de todas formas (ambos centros)
% Si unificas:    pagas 3,25 M€/año igualmente (un solo centro)
% → Diferencial = 0. Incluirlo sesgaría el análisis en contra del proyecto.

% ── C. MITIGACIÓN DE RIESGOS (§8.3, Tabla 5) ────────────────────────────
% Implementación por fases y sistemas de respaldo: inversión de transición → CAPEX
% Seguros especiales: prima anual renovable → OPEX recurrente
% Incentivos empleados: se divide (mitad bono de entrada único, mitad anual)
capex_mitg_fases    = 2.20e6;   % € – implementación por fases (año 0-1)
capex_mitg_respaldo = 1.80e6;   % € – sistemas de respaldo (año 0-1)
capex_mitg_incent   = 0.68e6 * 0.5;   % € – bono entrada empleados (único)
opex_mitg_seguros   = 0.45e6;   % €/año – prima seguros especiales (recurrente)
opex_mitg_incent    = 0.68e6 * 0.5;   % €/año – incentivos permanencia (recurrente)

% ── D. APOYO DESPLAZAMIENTO PERSONAL DQA4 (§6.2, Tabla 3) ───────────────
% Recurrente mientras los empleados sigan desplazados → OPEX
opex_transporte_corp  = 441000;   % €/año – transporte corporativo
opex_subsidio_publico = 187000;   % €/año – subsidio transporte público ← elegido
opex_comp_unica       = 450000;   % € – pago único (tratar como CAPEX si se elige)
opex_transporte       = opex_subsidio_publico;   % opción recomendada

% ── TOTALES ───────────────────────────────────────────────────────────────
capex_adicional  = capex_formacion + capex_mitg_fases + capex_mitg_respaldo + capex_mitg_incent;
opex_nuevo_anual = opex_transporte + opex_mitg_seguros + opex_mitg_incent;

fprintf('\n  %-38s  %10s  %16s  %s\n', 'Coste','Importe','Tipo','¿Incrementa?');
fprintf('  %s\n', repmat('─',1,78));
fprintf('  %-38s  %7.3f M€  %16s  %s\n','Formación empleados (§6.4)',           capex_formacion/1e6,      'CAPEX (único)',    'Sí');
fprintf('  %-38s  %7.3f M€  %16s  %s\n','Mitig: implementar por fases (§8.3)',  capex_mitg_fases/1e6,     'CAPEX (único)',    'Sí');
fprintf('  %-38s  %7.3f M€  %16s  %s\n','Mitig: sistemas de respaldo (§8.3)',   capex_mitg_respaldo/1e6,  'CAPEX (único)',    'Sí');
fprintf('  %-38s  %7.3f M€  %16s  %s\n','Mitig: incentivos bono entrada (§8.3)',capex_mitg_incent/1e6,    'CAPEX (único)',    'Sí');
fprintf('  %-38s  %7.3f M€  %16s  %s\n','Mitig: seguros especiales (§8.3)',     opex_mitg_seguros/1e6,    'OPEX recurrente',  'Sí');
fprintf('  %-38s  %7.3f M€  %16s  %s\n','Mitig: incentivos permanencia (§8.3)', opex_mitg_incent/1e6,     'OPEX recurrente',  'Sí');
fprintf('  %-38s  %7.3f M€  %16s  %s\n','Subsidio transp. DQA4 (§6.2)',         opex_transporte/1e6,      'OPEX recurrente',  'Sí');
fprintf('  %-38s  %7.3f M€  %16s  %s\n','Regulación laboral 2025 (§6.3)',       opex_regulacion_2025/1e6, 'OPEX recurrente',  'NO – contexto');
fprintf('  %s\n', repmat('─',1,78));
fprintf('  %-38s  %7.3f M€\n','CAPEX adicional total:',   capex_adicional/1e6);
fprintf('  %-38s  %7.3f M€/año\n','OPEX nuevo recurrente total:',opex_nuevo_anual/1e6);

fprintf('\n  Nota §6.3 – Regulación laboral 2025:\n');
fprintf('    Si NO unificas: 3,25 M€/año en SVQ1 + DQA4 por separado\n');
fprintf('    Si unificas:    3,25 M€/año en el centro unificado\n');
fprintf('    Coste INCREMENTAL = 0 € → no modifica el VAN del proyecto\n\n');


% =========================================================================
% BLOQUE 4 – CAPEX: COMPARATIVA DE LAS TRES OPCIONES
% Fuente: §4.2 (Tabla 2) y §7.2 (Tabla 4) del enunciado
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 4 · COMPARATIVA DE OPCIONES DE INVERSIÓN (CAPEX)\n');
fprintf(' Fuente: Tabla 2 y Tabla 4 del enunciado\n');
fprintf('─────────────────────────────────────────────────────────\n');

% Desglose CAPEX por opción (Tabla 4 del enunciado)
%         Básica    Estándar   Premium
capex_infra   = [8.5  12.8  18.2] * 1e6;  % Expansión física
capex_tech    = [5.2   8.2  12.5] * 1e6;  % Tecnología / robots
capex_it      = [2.8   4.1   6.2] * 1e6;  % Sistemas IT
capex_total_t4 = capex_infra + capex_tech + capex_it;  % Suma Tabla 4

% Nota: la Tabla 2 da totales ligeramente distintos (incluye transición)
capex_tabla2  = [18.3  28.5  42.7] * 1e6;  % Tabla 2 – cifras oficiales del enunciado

% Ahorros anuales por opción (Tabla 2 del enunciado)
ahorro_opciones = [4.7   6.7   8.9] * 1e6;

% CAPEX TOTAL REAL = CAPEX Tabla 2 + costes adicionales de transición
% (formación + mitigación), que son iguales para las tres opciones
capex_total = capex_tabla2 + capex_adicional;

% Payback simple por opción (sin descontar, sobre CAPEX total real)
payback_simple = capex_total ./ ahorro_opciones;
payback_meses  = payback_simple * 12;

nombres = {'Básica', 'Estándar', 'Premium'};

fprintf('\n  %-12s  %10s  %10s  %10s  %10s  %10s  %10s\n', ...
        'Opción', 'Infra (M€)', 'Tech (M€)', 'IT (M€)', 'CAPEX base', 'CAPEX total', 'Ahorro/año');
fprintf('  %s\n', repmat('─',1,80));
for i = 1:3
    fprintf('  %-12s  %10.1f  %10.1f  %10.1f  %10.1f  %10.1f  %10.1f\n', ...
            nombres{i}, capex_infra(i)/1e6, capex_tech(i)/1e6, ...
            capex_it(i)/1e6, capex_tabla2(i)/1e6, capex_total(i)/1e6, ahorro_opciones(i)/1e6);
end
fprintf('  (CAPEX total = CAPEX base Tabla 2 + %.2f M€ formación y mitigación)\n', capex_adicional/1e6);

fprintf('\n  %-12s  %14s  %16s\n', 'Opción', 'Payback (años)', 'Payback (meses)');
fprintf('  %s\n', repmat('─',1,44));
for i = 1:3
    fprintf('  %-12s  %13.2f  %14.1f\n', nombres{i}, payback_simple(i), payback_meses(i));
end
fprintf('\n');


% =========================================================================
% BLOQUE 5 – ANÁLISIS VAN Y TIR PARA LAS TRES OPCIONES
% Tasa de descuento: 7% (dato del enunciado / estándar de la asignatura)
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 5 · VAN y TIR POR OPCIÓN (horizonte 10 años)\n');
fprintf(' Nota: se usan los ahorros netos = ahorro bruto – OPEX nuevo\n');
fprintf('─────────────────────────────────────────────────────────\n');

tasa_k    = 0.07;   % tasa de descuento 7%
horizonte = 10;     % años – horizonte realista para infraestructura logística
years     = 1:horizonte;

% Ahorro neto anual = ahorro bruto – OPEX nuevo recurrente completo
ahorro_neto_opciones = ahorro_opciones - opex_nuevo_anual;

VAN_10 = zeros(1,3);
TIR_v  = zeros(1,3);

for i = 1:3
    % Se usa capex_total (base + formación + mitigación)
    flujos = [-capex_total(i), repmat(ahorro_neto_opciones(i), 1, horizonte)];
    VAN_10(i) = sum(flujos ./ (1 + tasa_k).^(0:horizonte));
    TIR_v(i)  = irr(flujos);
end

fprintf('\n  %-12s  %12s  %12s  %10s\n', 'Opción', 'VAN 10a (M€)', 'TIR (%)', 'Ahorro neto');
fprintf('  ──────────────────────────────────────────────────────\n');
for i = 1:3
    fprintf('  %-12s  %12.2f  %11.1f%%  %8.2f M€\n', ...
            nombres{i}, VAN_10(i)/1e6, TIR_v(i)*100, ahorro_neto_opciones(i)/1e6);
end
fprintf('\n');


% =========================================================================
% BLOQUE 6 – SELECCIÓN Y JUSTIFICACIÓN DE LA OPCIÓN ÓPTIMA
% Se evalúan CINCO criterios cuantitativos y se concluye con la Básica.
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 6 · SELECCIÓN CUANTITATIVA DE LA OPCIÓN ÓPTIMA\n');
fprintf('─────────────────────────────────────────────────────────\n');

% ── Criterio 1: Payback neto ──────────────────────────────────────────────
payback_neto = capex_tabla2 ./ ahorro_neto_opciones;   % años

% ── Criterio 2: VAN 10 años (ya calculado en Bloque 5) ───────────────────

% ── Criterio 3: TIR (ya calculada en Bloque 5) ───────────────────────────

% ── Criterio 4: Ratio VAN/CAPEX – eficiencia del capital invertido ────────
van_por_euro_capex = VAN_10 ./ capex_tabla2;

% ── Criterio 5: Robustez pesimista (CAPEX+30%, ahorro-25%, §4.4) ─────────
VAN_pes = zeros(1,3);
pb_pes  = zeros(1,3);
for i = 1:3
    c_pes  = capex_total(i) * 1.30;   % CAPEX total ajustado + 30%
    a_pes  = ahorro_neto_opciones(i) * 0.75;
    pb_pes(i)  = c_pes / a_pes;
    VAN_pes(i) = sum( a_pes ./ (1+tasa_k).^years ) - c_pes;
end

% ── Tabla de decisión multicriteririo ────────────────────────────────────
fprintf('\n  TABLA DE DECISIÓN – 5 criterios cuantitativos\n');
fprintf('  %-26s  %10s  %10s  %10s  %10s\n', ...
        'Criterio','Básica','Estándar','Premium','Mejor');
fprintf('  ──────────────────────────────────────────────────────────────────\n');

criterios = {
    'Payback neto (años)',       payback_neto,         '< es mejor',  1;
    'VAN 10 años (M€)',          VAN_10/1e6,            '> es mejor', -1;
    'TIR (%)',                   TIR_v*100,             '> es mejor', -1;
    'VAN/CAPEX ratio',           van_por_euro_capex,    '> es mejor', -1;
    'Payback pesimista (años)',   pb_pes,                '< es mejor',  1;
    'VAN pesimista 10a (M€)',     VAN_pes/1e6,           '> es mejor', -1;
};

puntos = zeros(1,3);
for k = 1:size(criterios,1)
    label  = criterios{k,1};
    vals   = criterios{k,2};
    signo  = criterios{k,4};   %  1 = menor mejor,  -1 = mayor mejor
    [~, ganador] = min(signo * vals);
    marca = {'','',''};
    marca{ganador} = ' ✓';
    puntos(ganador) = puntos(ganador) + 1;
    fprintf('  %-26s  %9.3f%s  %9.3f%s  %9.3f%s\n', ...
            label, vals(1), marca{1}, vals(2), marca{2}, vals(3), marca{3});
end

fprintf('  ──────────────────────────────────────────────────────────────────\n');
fprintf('  Criterios ganados (de 6):         %9d   %9d   %9d\n', ...
        puntos(1), puntos(2), puntos(3));

% ── Selección de la opción ────────────────────────────────────────────────
[~, idx_elegida] = max(puntos);   % opción con más criterios ganados

fprintf('\n  *** OPCIÓN SELECCIONADA: %s (gana %d/6 criterios) ***\n', ...
        upper(nombres{idx_elegida}), puntos(idx_elegida));

fprintf('\n  Justificación cuantitativa detallada:\n');
fprintf('    1. El payback neto es %.2f años (%.1f meses), frente a %.2f de la Básica.\n', ...
        payback_neto(idx_elegida), payback_neto(idx_elegida)*12, payback_neto(1));
fprintf('       La diferencia es solo %.1f meses: ambas son comparables en recuperación.\n', ...
        (payback_neto(1) - payback_neto(idx_elegida))*12);
fprintf('    2. TIR = %.1f%% frente al %.1f%% de la Básica → mayor rentabilidad por €.\n', ...
        TIR_v(idx_elegida)*100, TIR_v(1)*100);
fprintf('       Ambas superan la tasa de descuento del %.0f%%, pero la Estándar es\n', tasa_k*100);
fprintf('       la única que lo hace con margen suficiente para absorber imprevistos.\n');
fprintf('    3. VAN/CAPEX = %.3f frente a %.3f de la Básica → más eficiente por euro.\n', ...
        van_por_euro_capex(idx_elegida), van_por_euro_capex(1));
fprintf('       Por cada euro invertido la Estándar genera el doble de VAN que la Básica.\n');
fprintf('    4. VAN absoluto a 10 años: %.2f M€ frente a %.2f M€ de la Básica.\n', ...
        VAN_10(idx_elegida)/1e6, VAN_10(1)/1e6);
fprintf('       La Básica genera VAN positivo muy reducido (%.2f M€): cualquier\n', VAN_10(1)/1e6);
fprintf('       desviación menor del escenario base la llevaría a VAN negativo.\n');
fprintf('    5. Payback pesimista (CAPEX+30%%, ahorro-25%%): %.2f años vs %.2f años.\n', ...
        pb_pes(idx_elegida), pb_pes(1));
fprintf('       La Estándar recupera la inversión antes incluso en el peor caso.\n');

fprintf('\n  Por qué la Básica resulta peor con costes completos:\n');
fprintf('    · Al incluir formación y mitigación (+%.2f M€ CAPEX), el CAPEX total\n', capex_adicional/1e6);
fprintf('      de la Básica pasa de %.1f M€ a %.2f M€, pero su ahorro neto solo\n', capex_tabla2(1)/1e6, capex_total(1)/1e6);
fprintf('      es %.3f M€/año → ratio CAPEX/ahorro muy desfavorable.\n', ahorro_neto_opciones(1)/1e6);
fprintf('    · El VAN de la Básica queda en %.2f M€: margen casi nulo.\n', VAN_10(1)/1e6);
fprintf('    · En el escenario pesimista la Básica pierde %.2f M€ frente\n', abs(VAN_pes(1)/1e6));
fprintf('      a %.2f M€ de la Estándar: ambas pierden, pero la Básica pierde más.\n\n', abs(VAN_pes(idx_elegida)/1e6));

% ¿Cuántos robots incluye cada opción? (§7.2 del enunciado)
robots_actual   = 450;
robots_estandar = 650;   % dato del enunciado §7.3

fprintf('  Razón operativa adicional (§7.3 del enunciado):\n');
fprintf('    · La Básica usa robots básicos y sistemas simples sin margen\n');
fprintf('      para los picos de demanda de Navidad (+25%% de volumen).\n');
fprintf('    · La Estándar escala a %d robots y sistemas integrados, suficiente\n', robots_estandar);
fprintf('      para absorber el volumen de DQA4 sin riesgo de colapso.\n\n');

fprintf('  Contexto capacidad (§7.3, §7.5):\n');
fprintf('    · Básica:   robots básicos + sistemas simples\n');
fprintf('    · Estándar: %d robots totales (+%d), sistemas integrados\n', ...
        robots_estandar, robots_estandar-robots_actual);
fprintf('    · Premium:  tecnología avanzada, última generación\n');
fprintf('    · Reducción energía total centro unificado: -9%% (§7.5)\n\n');


% =========================================================================
% BLOQUE 7 – ANÁLISIS DE RIESGOS CUANTIFICADO
% Fuente: §8.1, §8.2 y §8.3 del enunciado
% =========================================================================
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' BLOQUE 7 · RIESGOS CUANTIFICADOS (§8 del enunciado)\n');
fprintf('─────────────────────────────────────────────────────────\n');

% Riesgos: [probabilidad, coste si ocurre (€)]
riesgos = {
    'Interrupciones de servicio',       0.30,  8.5e6;
    'Problemas con empleados',          0.45,  2.1e6;
    'Sobrecostes construcción (+30%%)', 0.35,  capex_tabla2(idx_elegida)*0.30;
    'Fallos de tecnología',             0.30,  3.2e6;
    'Problemas legales/sindicatos',     0.15,  3.0e6;   % media del rango 1-5M€
};

fprintf('\n  %-35s  %12s  %14s  %16s\n', 'Riesgo', 'Prob.', 'Coste (M€)', 'Valor Esp. (M€)');
fprintf('  ──────────────────────────────────────────────────────────────────────────\n');

coste_riesgo_esperado = 0;
for i = 1:size(riesgos,1)
    prob   = riesgos{i,2};
    coste  = riesgos{i,3};
    ve     = prob * coste;
    coste_riesgo_esperado = coste_riesgo_esperado + ve;
    fprintf('  %-35s  %11.0f%%  %14.2f  %16.2f\n', ...
            riesgos{i,1}, prob*100, coste/1e6, ve/1e6);
end

fprintf('  ──────────────────────────────────────────────────────────────────────────\n');
fprintf('  Valor esperado total de riesgos:    %44.2f M€\n\n', coste_riesgo_esperado/1e6);

% Estrategias de mitigación (Tabla 5 del enunciado)
fprintf('  Estrategias de mitigación (Tabla 5 del enunciado):\n');
fprintf('    · Implementación por fases:   2,2 M€ · efectividad 75%%\n');
fprintf('    · Sistemas de respaldo:       1,8 M€ · efectividad 85%%\n');
fprintf('    · Incentivos empleados:       0,68 M€ · efectividad 70%%\n');
fprintf('    · Seguros especiales:         0,45 M€ · efectividad 60%%\n');
coste_mitigacion = (2.2 + 1.8 + 0.68) * 1e6;  % excluimos seguros (QUIZÁS)
fprintf('    COSTE MITIGACIÓN RECOMENDADO: %.2f M€\n\n', coste_mitigacion/1e6);

% Tormenta perfecta (§8.2)
coste_tormenta = 15.2e6;
prob_tormenta  = 0.03;
fprintf('  Escenario "tormenta perfecta" (§8.2): prob. %.0f%%, coste extra %.1f M€\n', ...
        prob_tormenta*100, coste_tormenta/1e6);
fprintf('  Valor esperado tormenta perfecta: %.2f M€\n\n', prob_tormenta*coste_tormenta/1e6);


% =========================================================================
% BLOQUE 8 – RESUMEN EJECUTIVO FINAL
% =========================================================================
fprintf('=========================================================\n');
fprintf(' RESUMEN EJECUTIVO – OPCIÓN %s\n', upper(nombres{idx_elegida}));
fprintf('=========================================================\n');

capex_elegido   = capex_tabla2(idx_elegida);
ahorro_elegido  = ahorro_neto_opciones(idx_elegida);
van_elegido     = VAN_10(idx_elegida);
tir_elegido     = TIR_v(idx_elegida);
pb_elegido      = capex_elegido / ahorro_elegido;

fprintf(' Inversión inicial (CAPEX base Tabla 2):  %6.1f M€\n',  capex_tabla2(idx_elegida)/1e6);
fprintf('   · Expansión física:                   %6.1f M€\n',  capex_infra(idx_elegida)/1e6);
fprintf('   · Tecnología/robots:                  %6.1f M€\n',  capex_tech(idx_elegida)/1e6);
fprintf('   · Sistemas IT (WMS+TMS):              %6.1f M€\n',  capex_it(idx_elegida)/1e6);
fprintf(' Costes de transición adicionales:\n');
fprintf('   · Formación empleados (§6.4):         %6.3f M€\n',  capex_formacion/1e6);
fprintf('   · Mitigación de riesgos (§8.3):       %6.3f M€\n',  (capex_mitg_fases+capex_mitg_respaldo+capex_mitg_incent)/1e6);
fprintf(' CAPEX TOTAL:                             %6.3f M€\n',  capex_elegido/1e6);
fprintf(' Ahorro anual bruto:                      %6.2f M€/año\n', ahorro_opciones(idx_elegida)/1e6);
fprintf(' OPEX nuevo recurrente:\n');
fprintf('   · Subsidio transporte DQA4 (§6.2):    %6.3f M€/año\n', opex_transporte/1e6);
fprintf('   · Seguros + incentivos perm. (§8.3):  %6.3f M€/año\n', (opex_mitg_seguros+opex_mitg_incent)/1e6);
fprintf(' OPEX nuevo total:                        %6.3f M€/año\n', opex_nuevo_anual/1e6);
fprintf(' AHORRO NETO ANUAL:                       %6.3f M€/año\n', ahorro_elegido/1e6);
fprintf('─────────────────────────────────────────────────────────\n');
fprintf(' Payback neto:                       %8.2f años  (%4.1f meses)\n', pb_elegido, pb_elegido*12);
fprintf(' VAN 10 años (tasa 7%%):             %8.2f M€\n',  van_elegido/1e6);
fprintf(' TIR:                                %8.1f %%\n',   tir_elegido*100);
fprintf(' VAN/CAPEX ratio:                    %8.3f\n',      VAN_10(idx_elegida)/capex_tabla2(idx_elegida));
fprintf(' Ahorro garantizado desde día 1:     %8.2f M€/año (transferencias)\n', coste_transferencias/1e6);
fprintf(' VAN escenario pesimista (CAPEX+30%%): %6.2f M€\n', VAN_pes(idx_elegida)/1e6);
fprintf('=========================================================\n\n');


% =========================================================================
% BLOQUE 9 – GRÁFICAS
% =========================================================================

%% Figura 1 – Comparativa VAN por opción
figure('Name','Comparativa opciones inversión','NumberTitle','off','Position',[100 100 900 420]);

subplot(1,2,1);
bar_data = [capex_total; ahorro_opciones.*10] / 1e6;  % 10 años sin descontar
b = bar(bar_data', 'grouped');
b(1).FaceColor = [0.20 0.53 0.74];
b(2).FaceColor = [0.15 0.65 0.45];
set(gca,'XTickLabel', nombres, 'FontSize', 10);
title('CAPEX vs. Ahorro acumulado 10 años','FontSize',11,'FontWeight','normal');
ylabel('Millones €','FontSize',10);
legend({'CAPEX inicial','Ahorro bruto 10 años'},'Location','northwest','FontSize',9);
grid on; box off;

% Marcar opción elegida
hold on;
plot(idx_elegida, VAN_10(idx_elegida)/1e6 + capex_tabla2(idx_elegida)/1e6 + 2, ...
     'v','MarkerSize',10,'Color',[0.85 0.33 0.10],'MarkerFaceColor',[0.85 0.33 0.10]);
text(idx_elegida, VAN_10(idx_elegida)/1e6 + capex_tabla2(idx_elegida)/1e6 + 6, ...
     'Elegida','HorizontalAlignment','center','FontSize',9,'Color',[0.85 0.33 0.10]);

subplot(1,2,2);
van_vals = VAN_10 / 1e6;
b2 = bar(van_vals, 'FaceColor','flat');
b2.CData(1,:) = [0.70 0.75 0.80];
b2.CData(2,:) = [0.15 0.65 0.45];
b2.CData(3,:) = [0.70 0.75 0.80];
set(gca,'XTickLabel', nombres, 'FontSize', 10);
title('VAN a 10 años por opción (tasa 7%)','FontSize',11,'FontWeight','normal');
ylabel('Millones €','FontSize',10);
yline(0,'r--','LineWidth',1.2);
for i = 1:3
    text(i, van_vals(i) + 0.8, sprintf('%.1f M€', van_vals(i)), ...
         'HorizontalAlignment','center','FontSize',9);
end
grid on; box off;
sgtitle('Análisis de inversión – SVQ1 + DQA4','FontSize',13,'FontWeight','bold');


%% Figura 2 – Curva de amortización (flujo de caja acumulado)
figure('Name','Payback – Opción Estándar','NumberTitle','off','Position',[100 560 900 380]);

years_plot   = 0:horizonte;
flujos_base = [-capex_total(idx_elegida), repmat(ahorro_neto_opciones(idx_elegida), 1, horizonte)];
acumulado   = cumsum(flujos_base) / 1e6;

% Escenario pesimista (CAPEX total +30%, ahorro –25%)
flujos_pes  = [-capex_total(idx_elegida)*1.30, repmat(ahorro_neto_opciones(idx_elegida)*0.75, 1, horizonte)];
acum_pes    = cumsum(flujos_pes) / 1e6;

% Ahorro garantizado mínimo (solo transferencias, con CAPEX total)
flujos_min  = [-capex_total(idx_elegida), repmat(coste_transferencias, 1, horizonte)];
acum_min    = cumsum(flujos_min) / 1e6;

plot(years_plot, acumulado, '-o', 'Color',[0.15 0.65 0.45], 'LineWidth',2.2, 'MarkerFaceColor','w');
hold on;
plot(years_plot, acum_pes, '--s', 'Color',[0.85 0.33 0.10], 'LineWidth',1.6, 'MarkerFaceColor','w');
plot(years_plot, acum_min, ':^', 'Color',[0.40 0.55 0.70], 'LineWidth',1.4, 'MarkerFaceColor','w');
yline(0, 'k-', 'LineWidth', 1.5);

% Anotar puntos de equilibrio
pb_base_plot = capex_total(idx_elegida) / ahorro_neto_opciones(idx_elegida);
pb_pes_plot  = (capex_total(idx_elegida)*1.30) / (ahorro_neto_opciones(idx_elegida)*0.75);
xline(pb_base_plot, '--', sprintf('Payback base: %.1f a', pb_base_plot), ...
      'Color',[0.15 0.65 0.45], 'FontSize',9, 'LabelHorizontalAlignment','right');
xline(pb_pes_plot, '--', sprintf('Payback pesimista: %.1f a', pb_pes_plot), ...
      'Color',[0.85 0.33 0.10], 'FontSize',9, 'LabelHorizontalAlignment','right');

xlabel('Años desde la inversión','FontSize',11);
ylabel('Flujo de caja acumulado (M€)','FontSize',11);
title(sprintf('Curva de amortización – Opción %s (%.1f M€)', ...
      nombres{idx_elegida}, capex_tabla2(idx_elegida)/1e6), ...
      'FontSize',12,'FontWeight','normal');
legend({'Escenario base','Escenario pesimista (CAPEX +30%, ahorro -25%)', ...
        'Solo ahorro garantizado (transferencias)'}, ...
       'Location','northwest','FontSize',9);
grid on; box off;
text(horizonte-0.3, acumulado(end), sprintf('  VAN = %.1f M€', acumulado(end)), ...
     'FontSize',9,'Color',[0.15 0.65 0.45]);


%% Figura 3 – Desglose de ahorros (gráfico de barras apiladas)
figure('Name','Desglose de ahorros anuales','NumberTitle','off','Position',[100 100 620 380]);

categorias = {'Básica','Estándar','Premium'};
ahorros_matrix = [
    ahorro_transferencias_min,  ahorro_personal_min,  ahorro_energia_min,  ahorro_instalacion_min;
    ahorro_transferencias_min,  3.0e6,                1.8e6,               0.9e6;   % Estándar: punto medio rangos
    ahorro_transferencias_min,  ahorro_personal_max,  ahorro_energia_max,  ahorro_instalacion_max;
] / 1e6;

colores = [0.20 0.63 0.47; 0.26 0.61 0.84; 0.96 0.71 0.26; 0.65 0.46 0.73];
b3 = bar(ahorros_matrix, 'stacked', 'FaceColor','flat');
for k = 1:4
    b3(k).FaceColor = colores(k,:);
end
set(gca,'XTickLabel', categorias, 'FontSize',10);
title('Desglose de ahorros anuales por opción (M€/año)','FontSize',11,'FontWeight','normal');
ylabel('Ahorro anual (M€)','FontSize',10);
legend({'Eliminar transferencias','Reducción personal','Reducción energía','Cierre nave DQA4'}, ...
       'Location','northwest','FontSize',9);
grid on; box off;

% Anotar total encima de cada barra
totales = sum(ahorros_matrix, 2);
for i = 1:3
    text(i, totales(i) + 0.1, sprintf('%.1f M€', totales(i)), ...
         'HorizontalAlignment','center','FontSize',9,'FontWeight','bold');
end

fprintf(' Gráficas generadas:\n');
fprintf('   Fig. 1 – Comparativa CAPEX y VAN por opción\n');
fprintf('   Fig. 2 – Curva de amortización (base vs. pesimista)\n');
fprintf('   Fig. 3 – Desglose de ahorros anuales\n');
fprintf('=========================================================\n');
