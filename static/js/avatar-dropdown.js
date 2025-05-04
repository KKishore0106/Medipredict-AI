
document.addEventListener('DOMContentLoaded', function () {
    // Initialize avatar dropdown
    const avatarDropdown = document.querySelector('.avatar-dropdown-container');
    if (avatarDropdown) {
        const toggle = avatarDropdown.querySelector('.avatar-dropdown-toggle');
        const menu = avatarDropdown.querySelector('.avatar-dropdown-menu');
        
        if (toggle && menu) {
            // Close dropdown when clicking outside
            document.addEventListener('click', function (e) {
                if (!avatarDropdown.contains(e.target)) {
                    menu.classList.add('hidden');
                }
            });

            // Toggle dropdown on click
            toggle.addEventListener('click', function (e) {
                e.stopPropagation();
                menu.classList.toggle('hidden');
            });

            // Keyboard accessibility: open with Enter/Space
            toggle.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    menu.classList.toggle('hidden');
                }
            });

            // Close dropdown on Escape key
            document.addEventListener('keydown', function (e) {
                if (e.key === 'Escape') {
                    menu.classList.add('hidden');
                }
            });
        }
    }
});
    // Close dropdowns when clicking outside
    document.addEventListener('click', function (e) {
        if (![...dropdowns].some(dropdown => dropdown.contains(e.target))) {
            closeAllDropdowns();
        }
    });

    // Close dropdowns on Escape globally
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeAllDropdowns();
        }
    });

