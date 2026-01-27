# -*- coding: utf-8 -*-
"""
Script d'analyse des données d'eye-tracking pour classer les points de regard
dans différentes régions d'intérêt (ROIs), avec un système de mapping
simplifié où le rôle cible/distracteur est géré par la logique du code.
"""

import time
import glob
import sys
import os
from collections import defaultdict 

# --- Fonctions Utilitaires ---

def is_in_rect(x, y, rect_coords):
    """
    Vérifie si un point (x, y) se trouve à l'intérieur d'un rectangle.
    `rect_coords` doit être une liste ou un tuple: [x_min, y_min, x_max, y_max].
    Gère les coordonnées invalides (valeur 999999999).
    """
    if x == 999999999 or y == 999999999:
        return False # Point de donnée invalide

    x_min, y_min, x_max, y_max = rect_coords
    return x_min <= x <= x_max and y_min <= y <= y_max

def get_file_metadata(file_path):
    """
    Première passe : Collecte des métadonnées (résolution écran, fréquence d'échantillonnage).
    """
    time_step_ms = 4 # Valeur par défaut pour l'intervalle de temps entre les points de regard (en ms)
    screen_max_x, screen_max_y = 0, 0 # Résolution de l'écran

    found_rate = False
    found_gaze_coords = False
    with open(file_path, 'r') as current_file:
        for line in current_file:
            parts = line.strip().split()
            if not parts:
                continue

            if parts[0] == 'MSG':
                if len(parts) > 3 and parts[3] == 'RATE':
                    try:
                        time_step_ms = 1.0 / float(parts[4]) * 1000
                        found_rate = True
                    except (ValueError, IndexError):
                        print(f"Attention: Impossible de lire 'RATE' dans {file_path}. Utilisation de la valeur par défaut ({time_step_ms} ms).")
                elif len(parts) > 2 and parts[2] == "GAZE_COORDS":
                    try:
                        screen_max_x = float(parts[5])
                        screen_max_y = float(parts[6])
                        found_gaze_coords = True
                    except (ValueError, IndexError):
                        print(f"Attention: Impossible de lire 'GAZE_COORDS' dans {file_path}.")
            
            # Arrête la première passe si toutes les infos essentielles sont trouvées
            if found_rate and found_gaze_coords:
                break
    
    if screen_max_x == 0 or screen_max_y == 0:
        print(f"Erreur: Impossible de déterminer la résolution de l'écran pour {file_path}. Vérifiez le message 'GAZE_COORDS'.")
        return None, None, None
    
    return time_step_ms, screen_max_x, screen_max_y

def parse_gaze_data_and_trials(file_path, keyword_start_trial, keyword_end_trial, col_movie_L, col_movie_R, col_trial_index, col_side_trial):
    """
    Deuxième passe : Collecte des messages de début/fin de trial et des données de regard.
    """
    start_times = []
    end_times = []
    gaze_coords = defaultdict(tuple) # Stocke {timestamp: (x, y)}
    movie_L_names, movie_R_names, trial_indices, side_trials = [], [], [], []
    
    with open(file_path, 'r') as current_file:
        for line in current_file:
            parts = line.strip().split()
            if not parts:
                continue

            if parts[0] == 'MSG':
                if len(parts) > 2 and parts[2] == keyword_start_trial:
                    start_times.append(int(parts[1]))
                    movie_L_names.append(parts[col_movie_L].strip()) # .strip() pour nettoyer les noms
                    movie_R_names.append(parts[col_movie_R].strip()) # .strip() pour nettoyer les noms
                    trial_indices.append(parts[col_trial_index])
                    side_trials.append(parts[col_side_trial])
                elif len(parts) > 2 and parts[2] == keyword_end_trial:
                    end_times.append(int(parts[1]))
            elif parts[0].isdigit(): # Ligne contenant des données de regard
                try:
                    timestamp = int(parts[0])
                    if len(parts) > 2 and parts[1] != '.' and parts[2] != '.':
                        gaze_coords[timestamp] = (float(parts[1]), float(parts[2]))
                    else:
                        gaze_coords[timestamp] = (999999999, 999999999) # Marque comme invalide
                except (ValueError, IndexError):
                    # Fallback for malformed lines, mark as invalid
                    gaze_coords[int(parts[0])] = (999999999, 999999999) 
    
    return start_times, end_times, gaze_coords, movie_L_names, movie_R_names, trial_indices, side_trials

def process_single_trial(
    f_path, n, start_time, end_time, gaze_coords_all, movie_left_name, movie_right_name,
    trial_index, side_trial_code, offset, screen_max_x, screen_max_y,
    ROI_COORDS_MAP, VIDEO_TO_ROI_BASE_MAP, final_output_file
):
    """
    Traite les données de regard pour un seul essai et écrit les résultats.
    """
    # Filtre les données de regard pour le trial actuel
    current_trial_gaze_data = {
        t: xy for t, xy in gaze_coords_all.items() 
        if start_time - offset <= t < end_time
    }
    
    # Définit les zones générales d'affichage des vidéos 
    video_left_display_area = [0, 0, int(screen_max_x / 2), int(screen_max_y)]
    video_right_display_area = [int(screen_max_x / 2 + 1), 0, int(screen_max_x), int(screen_max_y)]

    # Détermine quelle vidéo est la cible (Geste) et le distracteur (Action)
    target_side_code = int(side_trial_code) # 1 = cible à droite, 2 = cible à gauche

    if target_side_code == 1: # Cible est à DROITE
        target_video_actual_name = movie_right_name # Doit être un Geste
        distractor_video_actual_name = movie_left_name # Doit être une Action
        
        target_display_area = video_right_display_area
        distractor_display_area = video_left_display_area
        target_side_suffix = "Right"
        distractor_side_suffix = "Left"
    else: # Cible est à GAUCHE
        target_video_actual_name = movie_left_name # Doit être un Geste
        distractor_video_actual_name = movie_right_name # Doit être une Action
        
        target_display_area = video_left_display_area
        distractor_display_area = video_right_display_area
        target_side_suffix = "Left"
        distractor_side_suffix = "Right"

    # --- Récupération des coordonnées ROI via le mapping ---

    # Extraire le nom de base du fichier vidéo sans le chemin ni l'extension
    base_target_video_name = os.path.splitext(os.path.basename(target_video_actual_name))[0]
    base_distractor_video_name = os.path.splitext(os.path.basename(distractor_video_actual_name))[0]

    # 1. Récupération du ROI pour la Cible (Geste)
    base_target_roi_name = VIDEO_TO_ROI_BASE_MAP.get(base_target_video_name)
    target_roi_key = f"{base_target_roi_name}_{target_side_suffix}_ROI" if base_target_roi_name else None

    if target_roi_key and target_roi_key in ROI_COORDS_MAP:
        target_roi_coords = ROI_COORDS_MAP[target_roi_key]
    else:
        print(f"AVERTISSEMENT: Clé ROI '{target_roi_key}' introuvable pour la vidéo cible '{target_video_actual_name}' dans ROI_COORDS_MAP. Utilisation de la zone complète de la vidéo cible comme ROI par défaut.")
        target_roi_coords = target_display_area # Fallback à la zone d'affichage complète

    # 2. Récupération du ROI pour le Distracteur (Action)
    base_distractor_roi_name = VIDEO_TO_ROI_BASE_MAP.get(base_distractor_video_name)
    distractor_roi_key = f"{base_distractor_roi_name}_{distractor_side_suffix}_ROI" if base_distractor_roi_name else None

    if distractor_roi_key and distractor_roi_key in ROI_COORDS_MAP:
        distractor_roi_coords = ROI_COORDS_MAP[distractor_roi_key]
    else:
        print(f"AVERTISSEMENT: Clé ROI '{distractor_roi_key}' introuvable pour la vidéo distractrice '{distractor_video_actual_name}' dans ROI_COORDS_MAP. Utilisation de la zone complète de la vidéo distractrice comme ROI par défaut.")
        distractor_roi_coords = distractor_display_area # Fallback à la zone d'affichage complète

    # Compteur de temps relatif dans le trial (pour la colonne 'time' dans le fichier de sortie)
    # Utilisez le timestamp réel pour un calcul plus précis du temps relatif
    effective_trial_start_timestamp = start_time - offset

    for t_stamp in sorted(current_trial_gaze_data.keys()):
        x_gaze, y_gaze = current_trial_gaze_data[t_stamp]
        
        # Ignore les données de regard invalides
        if x_gaze == 999999999 or y_gaze == 999999999:
            continue

        # Initialisation des drapeaux de catégorie (seront utilisés pour les colonnes regroupées)
        is_roi_t = 0
        is_roi_d = 0
        is_roni_t = 0
        is_roni_d = 0
        is_away = 0
        roi_label = "Unclassified" 

        # 5 condition application
        if is_in_rect(x_gaze, y_gaze, target_roi_coords):
            is_roi_t = 1
            roi_label = "ROI_T"
        elif is_in_rect(x_gaze, y_gaze, distractor_roi_coords):
            is_roi_d = 1
            roi_label = "ROI_D"
        elif is_in_rect(x_gaze, y_gaze, target_display_area): # Ancien full_target_video_area
            is_roni_t = 1
            roi_label = "RONI_T"
        elif is_in_rect(x_gaze, y_gaze, distractor_display_area): # Ancien full_distractor_video_area
            is_roni_d = 1
            roi_label = "RONI_D"
        else:
            is_away = 1
            roi_label = "Away"

        # --- Création des colonnes regroupées (Geste/Action) ---
        geste_roi = is_roi_t     # Attention sur le ROI du Geste (cible)
        geste_roni = is_roni_t   # Attention sur le RONI du Geste (cible)
        action_roi = is_roi_d    # Attention sur le ROI de l'Action (distracteur)
        action_roni = is_roni_d  # Attention sur le RONI de l'Action (distracteur)
        
        # Écrit les résultats dans le fichier de sortie
        final_output_file.write(" ".join([
            f_path, 
            str(t_stamp - effective_trial_start_timestamp),
            movie_left_name,
            movie_right_name,
            trial_index,
            side_trial_code,
            str(int(geste_roi)),
            str(int(geste_roni)),
            str(int(action_roi)),
            str(int(action_roni)),
            str(int(is_away)),
            roi_label 
        ]) + "\n")

# --- Définition des Régions d'Intérêt (ROIs) ---

# 1. ROI_COORDS_MAP:
ROI_COORDS_MAP = {
    # ------------ACTOR1-----------------------
    # --- ROI gesture (target) ---
    
    # Display L 
    "CommonGesture_Actor1_Left_ROI": [155, 548, 443, 620], # Common ROI for Gesture1, Gesture5, Gesture6 .
    "Gesture2_Actor1_Left_ROI": [155, 404, 227, 620],
    "Gesture3_Actor1_Left_ROI": [155, 512, 443, 620],
    "Gesture4_Actor1_Left_ROI": [170, 512, 347, 620],
    
    # Display R
    "CommonGesture_Actor1_Right_ROI": [838, 548, 1126, 620], # Common ROI for Gesture1, Gesture5, Gesture6 .
    "Gesture2_Actor1_Right_ROI": [838, 404, 982, 620],
    "Gesture3_Actor1_Right_ROI": [838, 512, 1126, 620],
    "Gesture4_Actor1_Right_ROI": [838, 512, 1030, 620],

    # --- ROI Action (distractor)---
    #Display L
    "CommonAction_Actor1_Left_ROI": [155, 548, 443, 620],# Common ROI for Action1, Action5, Action6 .
    "Action2_Actor1_Left_ROI": [155, 404, 227, 620],
    "Action3_Actor1_Left_ROI": [155, 512, 443, 620],
    "Action4_Actor1_Left_ROI": [170, 512, 347, 620],
    
    # Display R
    "CommonAction_Actor1_Right_ROI": [838, 548, 1126, 620],
    "Action2_Actor1_Right_ROI": [838, 404, 982, 620],
    "Action3_Actor1_Right_ROI": [838, 512, 1126, 620],
    "Action4_Actor1_Right_ROI": [838, 512, 1030, 620],
    
    #--------------ACTOR2-----------------
    # --- ROI gesture (target) ---
    # Display L 
    "CommonGesture_Actor2_Left_ROI": [155, 548, 443, 620],
    "Gesture2_Actor2_Left_ROI": [299, 404, 443, 620],
    "Gesture3_Actor2_Left_ROI": [155, 512, 443, 620],
    "Gesture4_Actor2_Left_ROI": [251, 512, 443, 620],
    
    # Display R
    "CommonGesture_Actor2_Right_ROI": [838, 548, 1126, 620],
    "Gesture2_Actor2_Right_ROI": [982, 404, 1126, 620],
    "Gesture3_Actor2_Right_ROI": [838, 512, 1126, 620],
    "Gesture4_Actor2_Right_ROI": [934, 512, 1126, 620],
    
    #-------ROI action (distractor)-----------
    # Display L 
    "CommonAction_Actor2_Left_ROI": [155, 548, 443, 620],
    "Action2_Actor2_Left_ROI": [299, 404, 443, 620],
    "Action3_Actor2_Left_ROI": [155, 512, 443, 620],
    "Action4_Actor2_Left_ROI": [251, 512, 443, 620],
    
    # Display R
    "CommonAction_Actor2_Right_ROI": [838, 548, 1126, 620],
    "Action2_Actor2_Right_ROI": [982, 404, 1126, 620],
    "Action3_Actor2_Right_ROI": [838, 512, 1126, 620],
    "Action4_Actor2_Right_ROI": [934, 512, 1126, 620],
}

# 2. VIDEO_TO_ROI_BASE_MAP: 
VIDEO_TO_ROI_BASE_MAP = {
    # --- Mappage pour les vidéos de l'Actor1 ---
    "Gesture1_Actor1": "CommonGesture_Actor1",
    "Gesture5_Actor1": "CommonGesture_Actor1",
    "Gesture6_Actor1": "CommonGesture_Actor1",
    "Gesture2_Actor1": "Gesture2_Actor1", 
    "Gesture3_Actor1": "Gesture3_Actor1", 
    "Gesture4_Actor1": "Gesture4_Actor1", 

    "Action1_Actor1": "CommonAction_Actor1",
    "Action2_Actor1": "Action2_Actor1",
    "Action3_Actor1": "Action3_Actor1",
    "Action4_Actor1": "Action4_Actor1",
    "Action5_Actor1": "CommonAction_Actor1",
    "Action6_Actor1": "CommonAction_Actor1",

    # --- Mappage pour les vidéos de l'Actor2 ---
    "Gesture1_Actor2": "CommonGesture_Actor2",
    "Gesture5_Actor2": "CommonGesture_Actor2",
    "Gesture6_Actor2": "CommonGesture_Actor2", 
    "Gesture2_Actor2": "Gesture2_Actor2", 
    "Gesture3_Actor2": "Gesture3_Actor2", 
    "Gesture4_Actor2": "Gesture4_Actor2", 

    "Action1_Actor2": "CommonAction_Actor2",
    "Action2_Actor2": "Action2_Actor2",
    "Action3_Actor2": "Action3_Actor2",
    "Action4_Actor2": "Action4_Actor2",
    "Action5_Actor2": "CommonAction_Actor2",
    "Action6_Actor2": "CommonAction_Actor2",
}

def main():
    # --- Initialisation et Gestion des Fichiers de Résultats ---

    # Cherche tous les fichiers .asc dans le répertoire courant
    asc_files = glob.glob('*.asc')

    if not asc_files:
        print("Aucun fichier .asc trouvé dans le répertoire courant. Le script va s'arrêter.")
        sys.exit()

    # Vérifie si un fichier de résultats existe déjà
    output_filename = 'Results.txt'
    if os.path.isfile(output_filename):
        user_choice = input(f"Un fichier '{output_filename}' existe déjà. Voulez-vous l'effacer (Y) ou créer un nouveau fichier (N) ? ").strip().upper()
        if user_choice == "Y":
            final_file = open(output_filename, 'w')
        elif user_choice == "N":
            new_filename = input("Veuillez donner un nouveau nom pour le fichier de résultats : ").strip()
            if not new_filename:
                print("Aucun nom de fichier fourni. Le script va s'arrêter.")
                sys.exit()
            output_filename = new_filename
            final_file = open(output_filename, 'w')
        else:
            print("La réponse doit être 'Y' ou 'N'. Le script va s'arrêter.")
            sys.exit()
    else:
        final_file = open(output_filename, 'w')

    final_file.write("participant time movie_L movie_R i side_trial Target_ROI Target_RONI Distractor_ROI Distractor_RONI Away ROI_Label\n")

    # --- Paramètres de l'expérience et du fichier .asc ---
    offset = 100 # Offset en ms pour le début du trial
    keyword_start_trial = 'START_TEST'
    keyword_end_trial = 'END_TEST'
    
    col_movie_L = 4         # Colonne du nom du film gauche dans le message START_TEST
    col_movie_R = 5         # Colonne du nom du film droit dans le message START_TEST
    col_trial_index = 3     # Colonne de l'index du trial
    col_side_trial = 6      # Colonne indiquant le côté de la cible (1=droite, 2=gauche)

    # --- Traitement de Chaque Fichier .asc ---
    for f_path in asc_files:
        print(f"Traitement du fichier : {f_path}")
        
        time_step_ms, screen_max_x, screen_max_y = get_file_metadata(f_path)
        if time_step_ms is None: # Erreur lors de la lecture des métadonnées
            continue

        start_times, end_times, gaze_coords, movie_L_names, movie_R_names, trial_indices, side_trials = \
            parse_gaze_data_and_trials(f_path, keyword_start_trial, keyword_end_trial, col_movie_L, col_movie_R, col_trial_index, col_side_trial)

        # Vérifie la cohérence du nombre de début/fin de trials
        if len(end_times) != len(start_times):
            print(f"Attention: Nombre de messages START/END de trial incohérent dans {f_path}.")
            trial_count = min(len(start_times), len(end_times))
            print(f"  Traitement du minimum ({trial_count}) de trials complets.")
        else:
            trial_count = len(start_times)
        
        if trial_count == 0:
            print(f"Aucun trial valide trouvé dans {f_path}. Fichier ignoré.")
            continue

        print(f"Nombre de trials à analyser : {trial_count}")
        
        # --- Traitement de chaque Trial ---
        for n in range(trial_count):
            process_single_trial(
                f_path, n, start_times[n], end_times[n], gaze_coords,
                movie_L_names[n], movie_R_names[n], trial_indices[n], side_trials[n],
                offset, screen_max_x, screen_max_y,
                ROI_COORDS_MAP, VIDEO_TO_ROI_BASE_MAP, final_file
            )

    # Ferme le fichier de résultats une fois tous les fichiers .asc traités
    final_file.close()
    print(f"\nAnalyse terminée. Les résultats ont été enregistrés dans le fichier '{output_filename}'.")

if __name__ == "__main__":
    main()
