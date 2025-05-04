document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('sidebar-toggle-btn');
    const sidebar = document.querySelector('.sidebar');

    // Check if sidebar state is stored in localStorage
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed) {
        sidebar.classList.add('collapsed');
    }

    // Add click event listener to toggle button
    toggleBtn.addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');
        
        // Save sidebar state to localStorage
        const isNowCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isNowCollapsed);

        // Update toggle button icon
        const icon = toggleBtn.querySelector('i');
        icon.classList.add('fa-bars');
    });

    // Save sidebar state in localStorage
    function saveSidebarState() {
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    }

    // Restore sidebar state from localStorage
    function restoreSidebarState() {
        const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        if (isCollapsed) {
            sidebar.classList.add('collapsed');
        }
    }

    // Add event listener for sidebar state changes
    sidebar.addEventListener('transitionend', saveSidebarState);

    // Restore sidebar state when page loads
    restoreSidebarState();
});
