document.addEventListener("DOMContentLoaded", function () {
    // Filtering functionality
    const filterToggles = document.querySelectorAll(".filter-checkbox input");
    const gridItems = document.querySelectorAll(".grid-item");
    const lightbox = document.querySelector(".lightbox");
    const lightboxImg = lightbox.querySelector("img");
    let currentImageIndex = 0;
    let visibleImages = []; // Track currently visible images for filtering

    // Update visible images when filters change
    function updateFilters() {
        const activeUserFilters = Array.from(document.querySelectorAll('[data-filter="user"]:checked')).map((checkbox) => checkbox.value);

        const activeTagFilters = Array.from(document.querySelectorAll('[data-filter="tag"]:checked')).map((checkbox) => checkbox.value);

        visibleImages = []; // Reset visible images array

        gridItems.forEach((item) => {
            const itemUser = item.dataset.user;
            const itemTags = item.dataset.tags.split(",").map((tag) => tag.trim());

            const userMatch = activeUserFilters.length === 0 || activeUserFilters.includes(itemUser);
            const tagMatch = activeTagFilters.length === 0 || activeTagFilters.some((tag) => itemTags.includes(tag));

            if (userMatch && tagMatch) {
                item.style.display = "";
                visibleImages.push(item.querySelector("img"));
            } else {
                item.style.display = "none";
            }
        });
    }

    // Initialize lightbox functionality
    function initLightbox() {
        const allImages = document.querySelectorAll(".grid-item img");
        const lightbox = document.querySelector(".lightbox");
        const lightboxImg = lightbox.querySelector("img");
        const lightboxInfo = lightbox.querySelector(".lightbox-info");
        let currentImageIndex = 0;
    
        allImages.forEach((img) => {
            img.addEventListener("click", () => {
                // 1) Figure out which images are "visible" (handled by your existing code)
                currentImageIndex = visibleImages.indexOf(img);
                if (currentImageIndex !== -1) {
                    // 2) Show image in lightbox
                    lightboxImg.src = img.src;
                    lightbox.classList.add("active");
                    document.body.style.overflow = "hidden";
    
                    // 3) Populate .lightbox-info
                    const parentItem = img.closest(".grid-item");
                    if (parentItem) {
                        const user = parentItem.dataset.user || "Unknown User";
                        const date = parentItem.dataset.date || "Unknown Date";
                        const group = parentItem.dataset.group || "";
                        const rawTags = parentItem.dataset.tags || "";
                        
                        // Turn tags into an array
                        const tagList = rawTags.split(",").map(t => t.trim()).filter(Boolean);
    
                        // Build any HTML you want
                        let infoHTML = `<p><strong>Uploaded By:</strong> ${user}</p>`;
                        if (group) {
                            infoHTML += `<p><strong>Group:</strong> ${group}</p>`;
                        }
                        infoHTML += `<p><strong>Date:</strong> ${date}</p>`;
                        
                        if (tagList.length > 0) {
                            infoHTML += `<div class="tag-section"><strong>Tags:</strong> `;
                            tagList.forEach(tag => {
                                infoHTML += `<span class="tag-badge">#${tag}</span> `;
                            });
                            infoHTML += `</div>`;
                        }
                        // Finally, place that HTML in the lightbox-info container
                        lightboxInfo.innerHTML = infoHTML;
                    }
                }
            });
        });

        // Close lightbox
        lightbox.querySelector(".close-lightbox").addEventListener("click", () => {
            lightbox.classList.remove("active");
            document.body.style.overflow = "";
        });

        // Close on background click
        lightbox.addEventListener("click", (e) => {
            if (e.target === lightbox) {
                lightbox.classList.remove("active");
                document.body.style.overflow = "";
            }
        });

        // Previous image
        lightbox.querySelector(".lightbox-prev").addEventListener("click", (e) => {
            e.stopPropagation();
            if (visibleImages.length > 0) {
                currentImageIndex = (currentImageIndex - 1 + visibleImages.length) % visibleImages.length;
                lightboxImg.src = visibleImages[currentImageIndex].src;
            }
        });

        // Next image
        lightbox.querySelector(".lightbox-next").addEventListener("click", (e) => {
            e.stopPropagation();
            if (visibleImages.length > 0) {
                currentImageIndex = (currentImageIndex + 1) % visibleImages.length;
                lightboxImg.src = visibleImages[currentImageIndex].src;
            }
        });

        // Keyboard navigation
        document.addEventListener("keydown", (e) => {
            if (!lightbox.classList.contains("active")) return;

            switch (e.key) {
                case "Escape":
                    lightbox.classList.remove("active");
                    document.body.style.overflow = "";
                    break;
                case "ArrowLeft":
                    if (visibleImages.length > 0) {
                        currentImageIndex = (currentImageIndex - 1 + visibleImages.length) % visibleImages.length;
                        lightboxImg.src = visibleImages[currentImageIndex].src;
                    }
                    break;
                case "ArrowRight":
                    if (visibleImages.length > 0) {
                        currentImageIndex = (currentImageIndex + 1) % visibleImages.length;
                        lightboxImg.src = visibleImages[currentImageIndex].src;
                    }
                    break;
            }
        });
    }

    // Initialize everything
    filterToggles.forEach((toggle) => {
        toggle.addEventListener("change", updateFilters);
    });

    // Toggle filter menu
    document.querySelector(".filter-toggle").addEventListener("click", function () {
        const filterDropdowns = document.querySelectorAll(".filter-dropdown");
        filterDropdowns.forEach((dropdown) => {
            dropdown.classList.toggle("show");
        });
    });

    // Initial setup
    updateFilters(); // Initialize visible images array
    initLightbox(); // Setup lightbox functionality
});
