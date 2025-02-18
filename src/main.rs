use eframe::egui;
use std::process::Command;
use serde::{Deserialize, Serialize};
use rfd::FileDialog;
use std::path::PathBuf;
use std::fs;
use std::path::Path;
use std::collections::HashMap;
use std::io::{self, Write};
use chrono;

#[derive(Serialize, Deserialize, Default)]
struct PathStorage {
    recent_paths: HashMap<String, String>,
    last_directory: Option<String>,
}

#[derive(Default)]
struct ContainerManager {
    containers: Vec<Container>,
    images: Vec<Image>,
    selected_container: Option<String>,
    new_container_name: String,
    new_image_name: String,
    selected_file_path: Option<PathBuf>,
    path_storage: PathStorage,
    iso_path: Option<PathBuf>,
    iso_name: String,
    path_to_load: Option<String>,
    debug_messages: Vec<String>,
    show_image_selection: bool,
    available_images: Vec<String>,
    pending_container_name: Option<String>,
}

#[derive(Serialize, Deserialize, Clone)]
struct Container {
    name: String,
    status: String,
    image: String,
    id: String,
    ports: String,
    command: String,
    created: String,
}

#[derive(Serialize, Deserialize, Clone)]
struct Image {
    name: String,
    tag: String,
}

impl ContainerManager {
    fn new(_cc: &eframe::CreationContext<'_>) -> Self {
        let mut app = Self::default();
        
        // Load saved paths
        if let Ok(data) = fs::read_to_string("path_storage.json") {
            if let Ok(storage) = serde_json::from_str(&data) {
                app.path_storage = storage;
            }
        }
        
        app.refresh_containers();
        app.refresh_images();
        app
    }

    fn log_debug(&mut self, message: &str) {
        let timestamp = chrono::Local::now().format("%H:%M:%S").to_string();
        let debug_msg = format!("[{}] {}", timestamp, message);
        println!("{}", debug_msg);
        self.debug_messages.push(debug_msg);
        
        if self.debug_messages.len() > 100 {
            self.debug_messages.remove(0);
        }
    }

    fn run_docker_command(&mut self, args: &[&str]) -> String {
        self.log_debug(&format!("Running: docker {}", args.join(" ")));
        
        let output = Command::new("docker")
            .args(args)
            .output()
            .expect("Failed to execute docker command");

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();

        if !stderr.is_empty() {
            self.log_debug(&format!("stderr: {}", stderr));
        }
        if !stdout.is_empty() {
            self.log_debug(&format!("stdout: {}", stdout));
        }

        stdout
    }

    fn refresh_containers(&mut self) {
        self.log_debug("Refreshing container list");
        self.containers.clear();
        
        let output = self.run_docker_command(&[
            "ps", 
            "-a", 
            "--format", 
            "{{.Names}}\t{{.Status}}\t{{.Image}}\t{{.ID}}\t{{.Ports}}\t{{.Command}}\t{{.CreatedAt}}"
        ]);

        for line in output.lines() {
            let parts: Vec<&str> = line.split('\t').collect();
            if parts.len() >= 7 {
                let container = Container {
                    name: parts[0].to_string(),
                    status: parts[1].to_string(),
                    image: parts[2].to_string(),
                    id: parts[3].to_string(),
                    ports: parts[4].to_string(),
                    command: parts[5].to_string(),
                    created: parts[6].to_string(),
                };
                self.containers.push(container);
            }
        }

        self.log_debug(&format!("Found {} containers", self.containers.len()));
    }

    fn refresh_images(&mut self) {
        let output = self.run_docker_command(&["images", "--format", "{{json .}}"]);
        self.images = output
            .lines()
            .filter_map(|line| serde_json::from_str::<Image>(line).ok())
            .collect();
    }

    fn container_exists(&mut self, name: &str) -> bool {
        let output = self.run_docker_command(&["ps", "-a", "--format", "{{.Names}}"]);
        output.lines().any(|line| line.trim() == name)
    }

    fn create_container(&mut self) {
        let container_name = self.new_container_name.clone();
        if container_name.is_empty() {
            self.log_debug("Container name is empty");
            return;
        }

        // Check if container already exists
        if self.container_exists(&container_name) {
            self.log_debug(&format!("Container '{}' already exists", container_name));
            return;
        }

        // Get available images and show selection window
        let images_output = self.run_docker_command(&["images", "--format", "{{.Repository}}:{{.Tag}}"]);
        self.available_images = images_output.lines()
            .map(|s| s.to_string())
            .collect();
        
        self.log_debug(&format!("Available images: {:?}", self.available_images));
        
        self.show_image_selection = true;
        self.pending_container_name = Some(container_name);
    }

    fn show_image_selection_dialog(&mut self, ctx: &egui::Context) {
        if self.show_image_selection {
            // Clone the data we need to avoid borrowing issues
            let available_images = self.available_images.clone();
            let mut selected_image = None;
            let mut should_close = false;

            egui::Window::new("Select Image")
                .collapsible(false)
                .resizable(false)
                .show(ctx, |ui| {
                    ui.heading("Select an image for the container");
                    
                    egui::ScrollArea::vertical().show(ui, |ui| {
                        for image in &available_images {
                            if ui.selectable_label(false, image).clicked() {
                                selected_image = Some(image.clone());
                                should_close = true;
                            }
                        }
                    });

                    if ui.button("Cancel").clicked() {
                        should_close = true;
                    }
                });

            // Handle selection after the window is closed
            if should_close {
                self.show_image_selection = false;
                if let Some(image) = selected_image {
                    if let Some(container_name) = self.pending_container_name.take() {
                        self.create_container_with_image(&container_name, &image);
                    }
                } else {
                    self.pending_container_name = None;
                }
            }
        }
    }

    fn create_container_with_image(&mut self, container_name: &str, image: &str) {
        self.log_debug(&format!("Creating container '{}' with image '{}'", container_name, image));
        
        let create_output = self.run_docker_command(&[
            "create",
            "-it",
            "--name", container_name,
            image,
            "/bin/bash"
        ]);

        if create_output.contains("Error") {
            self.log_debug(&format!("Error creating container: {}", create_output));
        } else {
            self.log_debug(&format!("Container created: {}", container_name));
            self.new_container_name.clear();
            self.refresh_containers();
            
            // Automatically start the container
            self.run_docker_command(&["start", container_name]);
            self.refresh_containers();
        }
    }

    fn remove_container(&mut self) {
        if let Some(name) = self.selected_container.clone() {
            self.run_docker_command(&["rm", "-f", &name]);
            self.selected_container = None;
            self.refresh_containers();
        }
    }

    fn start_container(&mut self) {
        if let Some(name) = self.selected_container.clone() {
            self.run_docker_command(&["start", &name]);
            self.refresh_containers();
        }
    }

    fn stop_container(&mut self) {
        if let Some(name) = self.selected_container.clone() {
            self.run_docker_command(&["stop", &name]);
            self.refresh_containers();
        }
    }

    fn save_container_state(&mut self) {
        let container_name = self.selected_container.clone();
        let image_name = self.new_image_name.clone();
        
        if let Some(name) = container_name {
            if !image_name.is_empty() {
                self.run_docker_command(&["commit", &name, &image_name]);
                self.log_debug(&format!("Saved container {} as image {}", name, image_name));
                self.new_image_name.clear();
                self.refresh_images();
            } else {
                self.log_debug("Image name is empty");
            }
        } else {
            self.log_debug("No container selected");
        }
    }

    fn save_path_storage(&self) {
        if let Ok(json) = serde_json::to_string(&self.path_storage) {
            fs::write("path_storage.json", json).ok();
        }
    }

    fn import_file(&mut self) {
        let mut dialog = FileDialog::new()
            .add_filter("All Supported Files", &["tar", "tar.gz", "iso"])
            .add_filter("Docker Images", &["tar", "tar.gz"])
            .add_filter("ISO Images", &["iso"]);

        if let Some(last_dir) = &self.path_storage.last_directory {
            dialog = dialog.set_directory(last_dir);
        }

        if let Some(path) = dialog.pick_file() {
            if let Some(parent) = path.parent() {
                self.path_storage.last_directory = Some(parent.to_string_lossy().to_string());
            }

            let path_str = path.to_string_lossy().to_string();
            let extension = path.extension()
                .and_then(|ext| ext.to_str())
                .unwrap_or("");

            self.path_storage.recent_paths.insert(
                path.file_name().unwrap_or_default().to_string_lossy().to_string(),
                path_str.clone()
            );
            self.save_path_storage();

            match extension.to_lowercase().as_str() {
                "iso" => {
                    self.iso_path = Some(path.clone());
                    self.iso_name = path.file_stem()
                        .and_then(|name| name.to_str())
                        .unwrap_or("custom-image")
                        .to_string();
                },
                _ => {
                    self.run_docker_command(&["load", "-i", &path_str]);
                    self.selected_file_path = Some(path);
                    self.refresh_images();
                }
            }
        }
    }

    fn convert_iso_to_image(&mut self) {
        if let Some(iso_path) = &self.iso_path {
            let iso_path_str = iso_path.to_string_lossy().to_string();
            let image_name = format!("{}:latest", self.iso_name);

            let dockerfile_content = format!(r#"
FROM scratch
ADD {} /
CMD ["/bin/bash"]
"#, iso_path_str);

            let temp_dir = std::env::temp_dir().join("iso_conversion");
            fs::create_dir_all(&temp_dir).expect("Failed to create temp directory");
            
            let dockerfile_path = temp_dir.join("Dockerfile");
            fs::write(&dockerfile_path, dockerfile_content).expect("Failed to write Dockerfile");

            self.run_docker_command(&[
                "build",
                "-t",
                &image_name,
                "-f",
                dockerfile_path.to_str().unwrap(),
                temp_dir.to_str().unwrap()
            ]);

            fs::remove_dir_all(temp_dir).ok();

            self.iso_path = None;
            self.refresh_images();
        }
    }

    fn show_debug_panel(&mut self, ui: &mut egui::Ui) {
        ui.group(|ui| {
            ui.heading("Debug Log");
            egui::ScrollArea::vertical()
                .max_height(150.0)
                .id_source("debug_scroll")
                .show(ui, |ui| {
                    for message in &self.debug_messages {
                        ui.label(message);
                    }
                });
        });
    }

    fn show_container_details(&self, ui: &mut egui::Ui, container: &Container) {
        ui.group(|ui| {
            ui.horizontal(|ui| {
                let status_color = if container.status.contains("Up") {
                    egui::Color32::GREEN
                } else {
                    egui::Color32::RED
                };
                
                ui.label(egui::RichText::new("⬤")
                    .color(status_color)
                    .size(16.0));
                
                ui.vertical(|ui| {
                    ui.heading(&container.name);
                    ui.label(&container.status);
                    ui.label(format!("Image: {}", &container.image));
                    ui.label(format!("ID: {}", &container.id));
                });
            });
        });
    }

    fn show_image_details(&self, ui: &mut egui::Ui, image: &Image) {
        ui.group(|ui| {
            ui.horizontal(|ui| {
                ui.label(
                    egui::RichText::new("⬤")
                        .color(egui::Color32::BLUE)
                        .size(16.0)
                );
                
                ui.vertical(|ui| {
                    ui.heading(format!("{}:{}", image.name, image.tag));
                });
            });
        });
    }

    fn show_recent_paths(&mut self, ui: &mut egui::Ui) {
        let paths: Vec<(String, String)> = self.path_storage.recent_paths
            .iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect();

        if !paths.is_empty() {
            ui.heading("Recent Files");
            
            for (name, path) in paths {
                ui.horizontal(|ui| {
                    ui.label(&name);
                    if ui.small_button("Load").clicked() {
                        self.path_to_load = Some(path.clone());
                    }
                });
            }

            if let Some(path) = self.path_to_load.take() {
                if Path::new(&path).exists() {
                    self.run_docker_command(&["load", "-i", &path]);
                    self.refresh_images();
                }
            }
        }
    }

    fn show_import_section(&mut self, ui: &mut egui::Ui) {
        ui.vertical(|ui| {
            if ui.button("Select File (Docker Image or ISO)").clicked() {
                self.import_file();
            }

            if let Some(path) = &self.selected_file_path {
                ui.horizontal(|ui| {
                    ui.label("Selected Docker image: ");
                    ui.label(path.to_string_lossy().to_string());
                });
            }

            if let Some(path) = &self.iso_path {
                ui.horizontal(|ui| {
                    ui.label("Selected ISO: ");
                    ui.label(path.to_string_lossy().to_string());
                });

                ui.horizontal(|ui| {
                    ui.label("Image name: ");
                    ui.text_edit_singleline(&mut self.iso_name);
                    if ui.button("Convert to Docker Image").clicked() {
                        self.convert_iso_to_image();
                    }
                });
            }

            ui.separator();
            self.show_recent_paths(ui);
        });
    }

    fn open_container_terminal(&mut self) {
        if let Some(name) = self.selected_container.clone() {
            // First ensure the container is running
            let status = self.run_docker_command(&["inspect", "--format", "{{.State.Running}}", &name]);
            if status.trim() != "true" {
                self.log_debug(&format!("Starting container {} before opening terminal", name));
                self.run_docker_command(&["start", &name]);
            }

            // Create the docker exec command
            let docker_cmd = format!("docker exec -it {} bash", name);
            
            // Open a new command prompt with the docker exec command
            self.log_debug("Opening terminal window");
            
            Command::new("cmd")
                .args(["/C", "start", "cmd", "/K", &docker_cmd])
                .spawn()
                .map_err(|e| self.log_debug(&format!("Failed to open terminal: {}", e)))
                .ok();
        } else {
            self.log_debug("No container selected");
        }
    }

    fn show_container_actions(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            if ui.button("Start").clicked() {
                self.start_container();
            }
            if ui.button("Stop").clicked() {
                self.stop_container();
            }
            if ui.button("Remove").clicked() {
                self.remove_container();
            }
            if ui.button("Open Terminal").clicked() {
                self.open_container_terminal();
            }
        });

        ui.horizontal(|ui| {
            ui.label("Save as image:");
            ui.text_edit_singleline(&mut self.new_image_name);
            if ui.button("Save").clicked() {
                self.save_container_state();
            }
        });
    }

    fn show_container_list(&mut self, ui: &mut egui::Ui) {
        // Clone the containers to avoid borrowing issues
        let containers = self.containers.clone();
        let selected = self.selected_container.clone();

        // Use a larger scroll area
        egui::ScrollArea::vertical()
            .id_source("containers_scroll")
            .min_scrolled_height(400.0)
            .show(ui, |ui| {
                for container in containers {
                    ui.group(|ui| {
                        ui.horizontal(|ui| {
                            // Status indicator
                            let status_color = if container.status.contains("Up") {
                                egui::Color32::GREEN
                            } else {
                                egui::Color32::RED
                            };
                            
                            ui.label(
                                egui::RichText::new("⬤")
                                    .color(status_color)
                                    .size(16.0)
                            );

                            // Container details in vertical layout
                            ui.vertical(|ui| {
                                // Name as selectable header
                                let is_selected = selected.as_ref() == Some(&container.name);
                                if ui.selectable_label(is_selected, &container.name).clicked() {
                                    self.selected_container = Some(container.name.clone());
                                }

                                // Metadata
                                ui.horizontal(|ui| {
                                    ui.label("Status:");
                                    ui.label(
                                        egui::RichText::new(&container.status)
                                            .color(status_color)
                                    );
                                });

                                ui.horizontal(|ui| {
                                    ui.label("Image:");
                                    ui.label(&container.image);
                                });

                                ui.horizontal(|ui| {
                                    ui.label("ID:");
                                    ui.label(
                                        egui::RichText::new(&container.id)
                                            .monospace()
                                    );
                                });

                                if !container.ports.is_empty() {
                                    ui.horizontal(|ui| {
                                        ui.label("Ports:");
                                        ui.label(&container.ports);
                                    });
                                }

                                ui.horizontal(|ui| {
                                    ui.label("Created:");
                                    ui.label(&container.created);
                                });

                                // Quick action buttons
                                ui.horizontal(|ui| {
                                    let container_name = container.name.clone();
                                    if container.status.contains("Up") {
                                        if ui.small_button("Stop").clicked() {
                                            self.selected_container = Some(container_name.clone());
                                            self.stop_container();
                                        }
                                        if ui.small_button("Terminal").clicked() {
                                            self.selected_container = Some(container_name.clone());
                                            self.open_container_terminal();
                                        }
                                    } else {
                                        if ui.small_button("Start").clicked() {
                                            self.selected_container = Some(container_name.clone());
                                            self.start_container();
                                        }
                                    }
                                    if ui.small_button("Remove").clicked() {
                                        self.selected_container = Some(container_name);
                                        self.remove_container();
                                    }
                                });
                            });
                        });
                    });
                    ui.add_space(4.0);
                }
            });
    }

    fn show_containers_panel(&mut self, ui: &mut egui::Ui) {
        ui.vertical(|ui| {
            ui.heading("Containers");
            
            // Create container input
            ui.horizontal(|ui| {
                ui.label("New container name:");
                ui.text_edit_singleline(&mut self.new_container_name);
                if ui.button("Create").clicked() {
                    self.create_container();
                }
            });

            self.show_container_list(ui);
            self.show_container_actions(ui);
        });
    }
}

impl eframe::App for ContainerManager {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Show image selection dialog if active
        self.show_image_selection_dialog(ctx);

        egui::CentralPanel::default().show(ctx, |ui| {
            // Debug panel
            self.show_debug_panel(ui);
            ui.separator();

            // Main layout
            ui.horizontal(|ui| {
                self.show_containers_panel(ui);
                ui.separator();
                self.show_import_section(ui);
            });
        });
    }
}

impl Drop for ContainerManager {
    fn drop(&mut self) {
        self.save_path_storage();
    }
}

fn main() -> eframe::Result<()> {
    let native_options = eframe::NativeOptions {
        initial_window_size: Some(egui::vec2(1024.0, 768.0)),
        ..Default::default()
    };
    
    eframe::run_native(
        "Docker Container Manager",
        native_options,
        Box::new(|cc| Box::new(ContainerManager::new(cc)))
    )
} 