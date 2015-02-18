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
