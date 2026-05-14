%% 1. PARÁMETROS DE ENTRADA (Misma configuración física)
num_filas = 50; 
num_cols = 100;
num_plantas = 3;
est_por_planta = num_filas * num_cols; 
total_estanterias = est_por_planta * num_plantas; 
puertas = [1, 50; 50, 10; 50, 90];
P = [0.50, 0.25, 0.25]; 
penalizacion_celdas = 12; 
dist_planta = [penalizacion_celdas, 2*penalizacion_celdas, 3*penalizacion_celdas];

% Variables para guardar los mejores resultados (ahora guardamos 6 parámetros)
mejor_coste_ind = inf;
mejor_coste_glob = inf;
mejores_params_ind = zeros(1,6); 
mejores_params_glob = zeros(1,6);

% Definimos los rangos para iterar
rango_pct_A = 0.05:0.05:0.30; 
rango_mov_A = 0.70:0.05:0.85;

for pct_A = rango_pct_A
    for movimientos_A = rango_mov_A
        
        % Ajuste automático de B y C
        pct_B = (1 - pct_A) * 0.20; 
        pct_C = 1 - pct_A - pct_B;
        movimientos_B = (1 - movimientos_A) * 0.75; 
        movimientos_C = 1 - movimientos_A - movimientos_B;

        %% 2. CÁLCULO DE LA MATRIZ f GLOBAL
        matriz_f = zeros(num_filas, num_cols, num_plantas);
        num_puertas = size(puertas, 1);
        for p = 1:num_plantas
            for r = 1:num_filas
                for c = 1:num_cols
                    f_val = 0;
                    for d = 1:num_puertas
                        dist_h = abs(r - puertas(d, 1)) + abs(c - puertas(d, 2));
                        f_val = f_val + P(d) * (dist_h + dist_planta(p));
                    end
                    matriz_f(r, c, p) = f_val;
                end
            end
        end

        %% 3. ESTRATEGIA 1: ABC INDIVIDUAL
        num_A_ind = round(est_por_planta * pct_A);
        num_B_ind = round(est_por_planta * pct_B);
        num_C_ind = est_por_planta - num_A_ind - num_B_ind;
        coste_total_ind = 0;
        
        for p = 1:num_plantas
            f_planta = matriz_f(:, :, p);
            f_ord = sort(f_planta(:));
            sA = sum(f_ord(1 : num_A_ind));
            sB = sum(f_ord(num_A_ind + 1 : num_A_ind + num_B_ind));
            sC = sum(f_ord(num_A_ind + num_B_ind + 1 : end));
            
            pA = movimientos_A / (num_A_ind * 3);
            pB = movimientos_B / (num_B_ind * 3);
            pC = movimientos_C / (num_C_ind * 3);
            
            coste_total_ind = coste_total_ind + (sA * pA) + (sB * pB) + (sC * pC);
        end

        %% 4. ESTRATEGIA 2: ABC GLOBAL
        num_A_glob = round(total_estanterias * pct_A);
        num_B_glob = round(total_estanterias * pct_B);
        num_C_glob = total_estanterias - num_A_glob - num_B_glob;
        f_ord_g = sort(matriz_f(:));
        
        sA_g = sum(f_ord_g(1 : num_A_glob));
        sB_g = sum(f_ord_g(num_A_glob + 1 : num_A_glob + num_B_glob));
        sC_g = sum(f_ord_g(num_A_glob + num_B_glob + 1 : end));
        
        coste_total_glob = (sA_g * (movimientos_A/num_A_glob)) + ...
                           (sB_g * (movimientos_B/num_B_glob)) + ...
                           (sC_g * (movimientos_C/num_C_glob));

        % Guardamos los 6 parámetros si encontramos un mejor coste
        if coste_total_ind < mejor_coste_ind
            mejor_coste_ind = coste_total_ind;
            mejores_params_ind = [pct_A, pct_B, pct_C, movimientos_A, movimientos_B, movimientos_C];
        end
        
        if coste_total_glob < mejor_coste_glob
            mejor_coste_glob = coste_total_glob;
            mejores_params_glob = [pct_A, pct_B, pct_C, movimientos_A, movimientos_B, movimientos_C];
        end
    end
end

%% 5. ANÁLISIS DE RESULTADOS FINAL
ahorro_absoluto = coste_total_ind - coste_total_glob;
ahorro_porcentaje = (ahorro_absoluto / coste_total_ind) * 100;

fprintf('======================================================\n');
fprintf('  RESULTADOS ÓPTIMOS (Breakdown ABC)\n');
fprintf('======================================================\n\n');

fprintf('MEJOR ESTRATEGIA INDIVIDUAL:\n');
fprintf('   Coste: %.2f\n', mejor_coste_ind);
fprintf('   Distribución porcentaje:   A: %.0f%%, B: %.0f%%, C: %.0f%%\n', mejores_params_ind(1)*100, mejores_params_ind(2)*100, mejores_params_ind(3)*100);
fprintf('   Distribución Movs:   A: %.0f%%, B: %.0f%%, C: %.0f%%\n\n', mejores_params_ind(4)*100, mejores_params_ind(5)*100, mejores_params_ind(6)*100);

fprintf('MEJOR ESTRATEGIA GLOBAL:\n');
fprintf('   Coste: %.2f\n', mejor_coste_glob);
fprintf('   Distribución porcentaje:   A: %.0f%%, B: %.0f%%, C: %.0f%%\n', mejores_params_glob(1)*100, mejores_params_glob(2)*100, mejores_params_glob(3)*100);
fprintf('   Distribución Movs:   A: %.0f%%, B: %.0f%%, C: %.0f%%\n', mejores_params_glob(4)*100, mejores_params_glob(5)*100, mejores_params_glob(6)*100);

fprintf('======================================================\n');

% Gráfica con los mejores valores encontrados
figure('Name', 'Comparativa Óptima', 'NumberTitle', 'off');
b = bar([1, 2], [mejor_coste_ind, mejor_coste_glob], 0.5);
b.FaceColor = 'flat';
b.CData(1,:) = [0.8 0.2 0.2]; % Rojo para la estrategia mala
b.CData(2,:) = [0.2 0.8 0.2]; % Verde para la estrategia buena
set(gca, 'XTickLabel', {'Estrategia 1: ABC por Planta', 'Estrategia 2: ABC Global 3D'});
ylabel('Coste Logístico Diario (f \times Movimientos)');
title(sprintf('Ahorro del %.2f%% en desplazamientos', ahorro_porcentaje));
grid on;