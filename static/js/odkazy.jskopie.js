document.addEventListener("DOMContentLoaded", function() {
    console.log("Inicializace skriptu pro odkazy_a_informace.html");
    
    // Získání modálních oken
    const odkazModal = document.getElementById("odkazModal");
    const infoModal = document.getElementById("infoModal");
    const souborModal = document.getElementById("souborModal");
    
    console.log("Modální okna:", 
                odkazModal ? "odkazModal OK" : "odkazModal chybí", 
                infoModal ? "infoModal OK" : "infoModal chybí",
                souborModal ? "souborModal OK" : "souborModal chybí");
    
    // Získání tlačítek pro otevření modálních oken
    const odkazBtn = document.getElementById("pridatOdkazBtn");
    const infoBtn = document.getElementById("pridatInfoBtn");
    const souborBtn = document.getElementById("nahratSouborBtn");
    
    console.log("Tlačítka pro modální okna:", 
                odkazBtn ? "pridatOdkazBtn OK" : "pridatOdkazBtn chybí",
                infoBtn ? "pridatInfoBtn OK" : "pridatInfoBtn chybí",
                souborBtn ? "nahratSouborBtn OK" : "nahratSouborBtn chybí");
    
    // Získání prvků pro zavření modálních oken
    const zavritOdkazBtn = document.getElementById("zavritOdkaz");
    const zavritInfoBtn = document.getElementById("zavritInfo");
    const zavritSouborBtn = document.getElementById("zavritSoubor");
    
    // Funkce pro otevření modálního okna
    function openModal(modal) {
        if (modal) {
            console.log("Otevírám modální okno:", modal.id);
            modal.style.display = "block";
            document.body.classList.add("modal-open");
        } else {
            console.error("Nelze otevřít modální okno - neexistuje!");
        }
    }
    
    // Funkce pro zavření modálního okna
    function closeModal(modal) {
        if (modal) {
            console.log("Zavírám modální okno:", modal.id);
            modal.style.display = "none";
            document.body.classList.remove("modal-open");
        }
    }
    
    // Přidání událostí pro otevření modálních oken
    if (odkazBtn) {
        odkazBtn.addEventListener("click", function(e) {
            console.log("Kliknuto na tlačítko přidat odkaz");
            e.preventDefault();
            openModal(odkazModal);
        });
    } else {
        console.warn("⚠️ Tlačítko pro přidání odkazu nenalezeno!");
    }
    
    if (infoBtn) {
        infoBtn.addEventListener("click", function(e) {
            console.log("Kliknuto na tlačítko přidat informaci");
            e.preventDefault();
            openModal(infoModal);
        });
    } else {
        console.warn("⚠️ Tlačítko pro přidání informace nenalezeno!");
    }
    
    if (souborBtn) {
        souborBtn.addEventListener("click", function(e) {
            console.log("Kliknuto na tlačítko nahrát soubor");
            e.preventDefault();
            openModal(souborModal);
        });
    } else {
        console.warn("⚠️ Tlačítko pro nahrání souboru nenalezeno!");
    }
    
    // Přidání událostí pro zavření modálních oken
    if (zavritOdkazBtn) {
        zavritOdkazBtn.addEventListener("click", function() {
            closeModal(odkazModal);
        });
    }
    
    if (zavritInfoBtn) {
        zavritInfoBtn.addEventListener("click", function() {
            closeModal(infoModal);
        });
    }
    
    if (zavritSouborBtn) {
        zavritSouborBtn.addEventListener("click", function() {
            closeModal(souborModal);
        });
    }
    
    // Zavření modálního okna při kliknutí mimo něj
    window.addEventListener("click", function(event) {
        if (event.target === odkazModal) {
            closeModal(odkazModal);
        } else if (event.target === infoModal) {
            closeModal(infoModal);
        } else if (event.target === souborModal) {
            closeModal(souborModal);
        }
    });
    
    // Přidání kategorie "nová" do výběru
    const kategorieSelect = document.getElementById("kategorie");
    const novaKategorieInput = document.getElementById("nova-kategorie");
    
    if (kategorieSelect && novaKategorieInput) {
        kategorieSelect.addEventListener("change", function() {
            if (this.value === "nová") {
                novaKategorieInput.style.display = "block";
            } else {
                novaKategorieInput.style.display = "none";
            }
        });
    }
    
    console.log("✅ Event handlery pro modální okna byly inicializovány");

    // Definice globální testovací funkce
    window.testOpenModal = function(modalName) {
        console.log("Testovací funkce volána pro:", modalName);
        if (modalName === 'odkaz' && odkazModal) {
            openModal(odkazModal);
        } else if (modalName === 'info' && infoModal) {
            openModal(infoModal);
        } else if (modalName === 'soubor' && souborModal) {
            openModal(souborModal);
        } else {
            console.error('❌ Neznámý modal nebo modal neexistuje:', modalName);
        }
    };
});