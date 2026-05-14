% =========================================================================
% OPTIMIZACIÓN DE LAYOUT DE ALMACÉN - MÉTODO DEL ÍNDICE f (DISEÑO ABC)
% =========================================================================
clear; clc; close all;

%% 1. VARIABLES AJUSTABLES (PARÁMETROS DE ENTRADA)
% -------------------------------------------------------------------------
% Dimensiones de la cuadrícula (ej. 50 filas x 100 columnas = 5000 estanterías)
num_filas = 50; 
num_cols = 100;
total_estanterias = num_filas * num_cols;

% Posiciones de las puertas o puntos de E/S [Fila, Columna]
% Puedes añadir tantas filas a esta matriz como puertas quieras.
puertas = [
    1, 50;      % Puerta 1 (Salida): Centro de la pared superior
    50, 10;     % Puerta 2 (Entrada): Esquina inferior izquierda
    50, 50      % Puerta 3 (Salida): Esquina inferior derecha
];

% Porcentaje de entradas/salidas (Pi) por cada puerta (deben sumar 1)
% El vector debe tener el mismo número de elementos que puertas.
P = [0.25, 0.50, 0.25]; 

% Porcentajes de inventario ABC
pct_A = 0.15;   % 15% Alta rotación
pct_B = 0.15;   % 15% Media rotación
pct_C = 0.70;   % 70% Baja rotación

%% 2. CÁLCULO DEL ÍNDICE f PARA CADA CELDA DE LA MATRIZ
% -------------------------------------------------------------------------
% Inicializamos la matriz de los índices f
matriz_f = zeros(num_filas, num_cols);
num_puertas = size(puertas, 1);

% Recorremos cada celda de la cuadrícula
for r = 1:num_filas
    for c = 1:num_cols
        f_val = 0;
        % Sumatorio de Pi * Dik para todas las puertas
        for d = 1:num_puertas
            % Cálculo de Dik usando Distancia Rectilínea (Manhattan)
            distancia_ik = abs(r - puertas(d, 1)) + abs(c - puertas(d, 2));
            f_val = f_val + P(d) * distancia_ik;
        end
        % Asignamos el valor calculado a la celda
        matriz_f(r, c) = f_val;
    end
end

%% 3. ASIGNACIÓN ABC (ZONIFICACIÓN)
% -------------------------------------------------------------------------
% Calculamos el número de estanterías exactas para cada categoría
num_A = round(total_estanterias * pct_A);
num_B = round(total_estanterias * pct_B);
num_C = total_estanterias - num_A - num_B; % El resto para asegurar que suman el total

% Convertimos la matriz en un vector columna para ordenarla fácilmente
% sort nos devuelve los valores ordenados de menor a mayor y sus índices originales
[~, indices_ordenados] = sort(matriz_f(:));

% Creamos la matriz de asignación final (1=A, 2=B, 3=C)
matriz_ABC = zeros(num_filas, num_cols);

% Asignamos Producto A (menor f, posiciones más cercanas/favorables)
matriz_ABC(indices_ordenados(1:num_A)) = 1;

% Asignamos Producto B (siguientes posiciones)
matriz_ABC(indices_ordenados(num_A + 1 : num_A + num_B)) = 2;

% Asignamos Producto C (las posiciones con mayor f, más alejadas)
matriz_ABC(indices_ordenados(num_A + num_B + 1 : end)) = 3;

%% 4. VISUALIZACIÓN GRÁFICA DEL RESULTADO
% -------------------------------------------------------------------------
figure('Name', 'Zonificación ABC del Almacén', 'NumberTitle', 'off');
imagesc(matriz_ABC);

% Configuración de colores: Verde (A), Amarillo (B), Rojo (C)
colormap([0.2 0.8 0.2; 1 0.8 0; 0.8 0.2 0.2]); 

% Ajustes estéticos del gráfico
colorbar('Ticks', [1.33, 2, 2.66], 'TickLabels', {'Zona A (15%)', 'Zona B (15%)', 'Zona C (70%)'});
title('Distribución Óptima de Estanterías (Método del Índice f)');
xlabel('Columnas');
ylabel('Filas');
axis equal tight;
hold on;

% Dibujamos las puertas en el plano para referenciar
for d = 1:num_puertas
    plot(puertas(d, 2), puertas(d, 1), 'kx', 'MarkerSize', 12, 'LineWidth', 3);
    text(puertas(d, 2) + 2, puertas(d, 1), sprintf('P%d', d), 'FontWeight', 'bold');
end
hold off;

%% 5. FIGURA 2: VISUALIZACIÓN DEL MAPA DE VALORES f
% -------------------------------------------------------------------------
figure('Name', 'Mapa de Valores f', 'NumberTitle', 'off');
% Mostramos la matriz_f directamente
imagesc(matriz_f);

% Usamos un mapa de calor clásico (jet o parula). 'jet' va de azul (bajo) a rojo (alto).
colormap(gca, jet); 
c = colorbar;
c.Label.String = 'Valor del índice f (Coste logístico)';
title('Mapa de Calor del Índice f (Suma ponderada de distancias)');
xlabel('Columnas');
ylabel('Filas');
axis equal tight;
hold on;

% Dibujamos las puertas con color blanco para que resalten sobre los colores fuertes
for d = 1:num_puertas
    plot(puertas(d, 2), puertas(d, 1), 'wx', 'MarkerSize', 12, 'LineWidth', 3);
    text(puertas(d, 2) + 2, puertas(d, 1), sprintf('P%d', d), 'Color', 'white', 'FontWeight', 'bold');
end
hold off;