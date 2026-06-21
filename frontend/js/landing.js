function alternarMenuLanding() {
    const menu = document.getElementById("landing-nav");

    if (!menu) {
        return;
    }

    menu.classList.toggle("aberto");
}


document.addEventListener("click", (event) => {
    const menu = document.getElementById("landing-nav");
    const botao = document.querySelector(".btn-menu-mobile");

    if (
        !menu
        || !botao
    ) {
        return;
    }

    const clicouNoMenu = menu.contains(event.target);
    const clicouNoBotao = botao.contains(event.target);

    if (
        !clicouNoMenu
        && !clicouNoBotao
    ) {
        menu.classList.remove("aberto");
    }
});


window.alternarMenuLanding = alternarMenuLanding;