$( document ).ready( function() {

  $("#addBtn").click( function( event ) {
    event.preventDefault();
    add_post();
  });

  function add_post() {
    $.ajax({
      url: "/add",
      type: "POST",
      dataType: 'json',
      data: { "title": $("#title").val(), 'text': $("#text").val()},
      success: success
    });
  }

  function success( response ) {
    $("#addBtn").trigger('reset');
    var template = "<article id='entry={{id}}'>"+
                    "<a href='/detail/{{id}}'><h1 class='headingLink'>{{title}}</h1></a>"+
                    "<p><small>{{created}}</small>"+
                    "<div>{{{text}}}</br>"+
                    "<hr class='titleDivider'></div>"+
                    "</article>";
    var rendered = Mustache.render(template, response);
    $(".createForm").after(rendered);
    $(".createForm").hide('slow');
  }

$("#submitBtn").click( function( event ) {
    event.preventDefault();
    update_post();
  });

  function update_post() {
    var id = $("article").attr("id")
    $.ajax({
      url: "/edit",
      type: "POST",
      dataType: 'json',
      data: { "id": id, "title": $("#title").val(), "text": $("#text").val()},
      success: upd_success
    });
  }
  function upd_success( response ) {
    $("#submitBtn").trigger('reset');
    var template = "<div class='detailForm'>"+
                    "<article id='{{id}}'>"+
                    "<h1 class='headingLink'>{{title}}</h1>"+
                    "<p><small>{{created}}</small></p>"+
                    "<div>{{{text}}}</br></br>"+
                    "<hr class='titleDivider'>"+
                    "</div></article></div>";
    var updated = Mustache.render(template, response);
    $(".editForm").after(updated);
    $(".editForm").hide('slow');
  }

  $( function() {
    $('#editBtn').click( function() {
      $('.detailForm').hide('slow', function() {
        $('.editForm').show('slow');
      });
    });
  });

  $( function() {
    $('#cancelBtn').click( function() {
      $('.editForm').hide('slow', function() {
        $('.detailForm').show('slow');
      });
    });
  });

  $( function() {
    $('#createBtn').click( function() {
      $('.createForm').show('slow');
    });
  });

});
