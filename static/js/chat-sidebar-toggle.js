document.addEventListener('DOMContentLoaded', function() {
    // Select DOM elements
    const toggleBtn = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const chatInputContainer = document.querySelector('.chat-input-container');
    
    // Check if sidebar state is stored in localStorage
    const isCollapsed = localStorage.getItem('chatSidebarCollapsed') === 'true';
    
    // Function to update layout based on sidebar state
    function updateLayout(collapsed) {
        if (collapsed) {
            sidebar.classList.add('collapsed');
            
            // For mobile, handle differently
            if (window.innerWidth <= 640) {
                sidebar.classList.remove('show');
                sidebar.style.transform = 'translateX(-100%)';
            } else {
                sidebar.style.transform = 'translateX(0)';
            }
        } else {
            sidebar.classList.remove('collapsed');
            
            // For mobile, show sidebar
            if (window.innerWidth <= 640) {
                sidebar.classList.add('show');
                sidebar.style.transform = 'translateX(0)';
            } else {
                sidebar.style.transform = '';
            }
        }
    }
    
    // Initialize sidebar state
    updateLayout(isCollapsed);
    
    // Add click event listener to toggle button
    toggleBtn.addEventListener('click', function() {
        const willBeCollapsed = !sidebar.classList.contains('collapsed');
        
        // Toggle the collapsed state
        updateLayout(willBeCollapsed);
        
        // Save state to localStorage
        localStorage.setItem('chatSidebarCollapsed', willBeCollapsed.toString());
    });
    
    // Handle window resize events
    window.addEventListener('resize', function() {
        const isCurrentlyCollapsed = sidebar.classList.contains('collapsed');
        updateLayout(isCurrentlyCollapsed);
    });
    
    // Add click event listener to close sidebar when clicking outside (mobile only)
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 640 && 
            !sidebar.contains(event.target) && 
            !toggleBtn.contains(event.target) && 
            sidebar.classList.contains('show')) {
            updateLayout(true);
            localStorage.setItem('chatSidebarCollapsed', 'true');
        }
    });
});