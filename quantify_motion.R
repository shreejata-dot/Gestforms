install.packages("rlang")
install.packages("vctrs")
install.packages("cli")

install.packages("SpatialPack")

install.packages(c("av", "magick", "imager"))

#read video frames
library(av)
library(magick)
library(imager)
library(ggplot2)
library(SpatialPack)
library(dplyr)
library(stringr)

#Video processing

process_video <- function(video_path, fps = 30, scale = "25%") {
  
  frames <- av_video_images(video_path, fps = fps)
  
  gray_frames <- lapply(frames, function(img) {
    image_read(img) |>
      image_convert(colorspace = "gray") |>
      image_scale(scale)
  })
  
  n <- length(gray_frames)
  
  pixel_changes <- numeric(n - 1)
  ssim_changes  <- numeric(n - 1)
  motion_counts <- numeric(n - 1)
  
  for (i in 2:n) {
    img1 <- magick2cimg(gray_frames[[i - 1]])
    img2 <- magick2cimg(gray_frames[[i]])
    
    diff <- abs(img2 - img1)
    diff[diff <= 0.05] <- 0
    
    pixel_changes[i - 1] <- mean(diff)
    motion_counts[i - 1] <- sum(diff > 0.1)
    
    mat1 <- as.matrix(img1[,,1,1])
    mat2 <- as.matrix(img2[,,1,1])
    
    ssim_val <- SSIM(mat1, mat2)$SSIM
    ssim_changes[i - 1] <- 1 - ssim_val
  }
  
  time <- (1:(n - 1)) / fps
  
  data.frame(
    video = basename(video_path),
    time = time,
    pixel_change = pixel_changes,
    ssim_change = ssim_changes,
    motion_count = motion_counts
  )
  
}

# Plot for each videos
video_path <- "/Users/Administrateur/Desktop/eyetracking/videos"

video_files <- list.files(video_path,
                          pattern = "(Action|Gesture)[1-6]_Actor[12].*\\.mov", 
                          full.names = TRUE
)

all_data <- do.call(rbind,lapply(video_files, function(v) {
  df <- process_video(v)
  df$type <- ifelse(
    grepl("Action", v), "Action", "Gesture"
  )
  df
})
)

#Pixel change for each action/gesture videos
videos <- unique(all_data$video)

for (v in videos) {
  df_v <- subset(all_data, video == v)
  
  p <- ggplot(df_v, aes(time, pixel_change)) +
    geom_line() +
    labs(
      title = v,
      x = "Time (s)",
      y = "Pixel change", 
    ) +
    theme_minimal()
  
  print(p)
}
