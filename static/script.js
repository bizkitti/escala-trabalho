function abrirSheet(colab, data, regime, horario, grupo) {
    document.getElementById("sheetColaborador").innerText = colab || "";
    document.getElementById("sheetData").innerText        = data || "";
    document.getElementById("sheetRegime").innerText      = regime || "";
    document.getElementById("sheetHorario").innerText     = horario || "";
    document.getElementById("sheetGrupo").innerText       = grupo || "";

    document.getElementById("bottomSheet").classList.add("active");
}

function fecharSheet() {
    document.getElementById("bottomSheet").classList.remove("active");
}
